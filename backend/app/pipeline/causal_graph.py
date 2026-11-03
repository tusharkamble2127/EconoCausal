"""
Causal DAG definition and refutation tests (Volume I Chapter 8.4,
Volume II Chapter 12 Days 4 and 11).

Owned by Member 1 (Causal Modeling Engineer, Volume II Chapter 4.1).

Uses DoWhy to make the causal assumptions (confounders -> treatment,
confounders -> outcome, treatment -> outcome) explicit, and to run
refutation tests that provide the Mid Review evidence that the estimated
effect is not an artifact of confounding or noise (Volume II Chapter 12,
Day 11).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from dowhy import CausalModel

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RefutationOutcome:
    test_name: str
    passed: bool
    details: Dict


def build_model(df: pd.DataFrame, feature_names: List[str], treatment_col: str = "treatment", outcome_col: str = "outcome") -> CausalModel:
    """Build a DoWhy CausalModel with an explicit causal graph:
    confounders -> treatment, confounders -> outcome, treatment -> outcome.
    """
    logger.info("Building causal DAG with %d confounders", len(feature_names))
    model = CausalModel(
        data=df,
        treatment=treatment_col,
        outcome=outcome_col,
        common_causes=feature_names,
    )
    return model


def identify_and_estimate(model: CausalModel):
    """Identify the causal estimand and produce a baseline DoWhy estimate.

    This baseline estimate is used only to feed DoWhy's refutation tests;
    the production ITE/ATE estimates come from EconML's Double ML in
    pipeline/dml_model.py (Volume II Chapter 11.4).
    """
    identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        identified_estimand,
        method_name="backdoor.linear_regression",
    )
    return identified_estimand, estimate


def run_refutation_tests(model: CausalModel, identified_estimand, estimate) -> List[RefutationOutcome]:
    """Run the standard refutation-test suite (Volume II Chapter 12, Day 11)
    using DoWhy's native refutation API.

    A test is considered "passed" if the refuted estimate's new effect
    remains close to the original estimate (for random_common_cause) or
    collapses toward zero as expected (for placebo_treatment).
    """
    results: List[RefutationOutcome] = []
    original_effect = float(estimate.value)

    refuters = [
        ("placebo_treatment", "placebo_treatment_refuter", {"random_seed": 42}),
        ("random_common_cause", "random_common_cause", {"random_seed": 42}),
        ("data_subset", "data_subset_refuter", {"random_seed": 42}),
    ]

    for test_name, method_name, kwargs in refuters:
        try:
            t0 = time.time()
            refutation = model.refute_estimate(
                identified_estimand,
                estimate,
                method_name=method_name,
                **kwargs,
            )
            elapsed = time.time() - t0

            new_effect = float(refutation.new_effect)
            refutation_result = getattr(refutation, "refutation_result", {}) or {}
            is_significant = refutation_result.get("is_statistically_significant", None)

            if test_name == "placebo_treatment":
                passed = bool(abs(new_effect) < abs(original_effect) or abs(new_effect) < 0.05)
            elif test_name == "random_common_cause":
                delta = abs(new_effect - original_effect)
                passed = bool(delta < max(0.1 * abs(original_effect), 0.05))
            elif test_name == "data_subset":
                delta = abs(new_effect - original_effect)
                passed = bool(delta < max(0.15 * abs(original_effect), 0.05))
            else:
                passed = False

            details = {
                "new_effect": new_effect,
                "original_effect": original_effect,
                "elapsed_s": round(elapsed, 3),
                "refutation_type": refutation.refutation_type,
                "is_statistically_significant": bool(is_significant) if is_significant is not None else None,
            }
            results.append(RefutationOutcome(test_name, passed, details))
        except Exception as exc:  # pragma: no cover - defensive, logged for audit
            logger.error("%s refutation failed: %s", test_name, exc)
            results.append(RefutationOutcome(test_name, False, {"error": str(exc)}))

    logger.info("Refutation tests completed: %s", [(r.test_name, r.passed) for r in results])
    return results
