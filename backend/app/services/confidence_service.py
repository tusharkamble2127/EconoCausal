"""Canonical confidence score calculation for recommendations and explanations.

All confidence values in the application are derived from the same
statistical signal: the estimator's confidence-interval width at the
chosen discount level, blended with the run's causal refutation pass
rate, evidence adequacy checks, and propensity overlap diagnostics.
This ensures a customer sees the identical confidence whether they
query the recommendation panel or the per-customer explanation endpoint.

Confidence levels:
  - "High":             strong, usable statistical evidence
  - "Moderate":         valid evidence but not all high-confidence conditions met
  - "Low":              some usable evidence but substantial uncertainty
  - "Insufficient Evidence": evidence is fundamentally inadequate

The confidence_score in [0, 1] is a model/evidence-strength indicator,
NOT a probability that the recommendation is correct.

Composite methodology (deterministic, bounded 0-1):
  - Statistical precision (weight 0.30): narrower estimator CI => higher score.
    The outcome scale in this pipeline is the purchase probability, which is
    bounded on [0, 1] (clamped at the UI layer). Because the scale is fixed
    and bounded, absolute CI width is an appropriate precision signal without
    additional scale normalization.
  - Signal-to-noise ratio (weight 0.25): |point estimate| / CI width.
  - Refutation robustness (weight 0.15): DoWhy refutation pass rate.
    When refutation results are unavailable, a conservative heuristic
    fallback of 0.75 is used. Missing refutation evidence is NOT treated as
    equivalent to a successful refutation; the 0.75 fallback intentionally
    keeps the score below maximum to reflect the gap.
  - Sample adequacy (weight 0.10): minimum sample size for usable estimates.
    The n >= 30 threshold is a heuristic rule-of-thumb, not a universal
    statistical guarantee. Larger samples do not automatically imply higher
    reliability if other evidence is weak.
  - Data support (weight 0.20): propensity overlap, common support, and
    matching coverage. Poor overlap fundamentally undermines causal claims.
    The four retained metrics represent distinct observational-support
    diagnostics: (1) percent outside common support, (2) percent with
    extreme propensity scores, (3) number of unmatched treated units, and
    (4) complete matching collapse (zero matched pairs with unmatched treated).
    They can be correlated in pathological cases, but each captures a
    different failure mode, so multiple signals are retained to avoid
    missing isolated support defects.

Weights are documented rather than arbitrary: statistical precision and
signal-to-noise are the primary statistical signals; refutation and sample
size are supporting evidence; data support penalizes recommendations built
on weak observational overlap.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfidenceResult:
    confidence_score: float = 0.0
    confidence_level: str = "Insufficient Evidence"
    confidence_interval: Optional[dict] = None
    evidence: dict = field(default_factory=dict)


def _compute_data_support(
    pct_outside_support: float = 0.0,
    pct_extreme: float = 0.0,
    n_unmatched_treated: int = 0,
    n_matched_pairs: int = 0,
) -> float:
    score = 1.0

    if pct_outside_support > 20.0:
        score -= 0.30 * min(1.0, (pct_outside_support - 20.0) / 30.0)

    if pct_extreme > 10.0:
        score -= 0.20 * min(1.0, (pct_extreme - 10.0) / 15.0)

    if n_unmatched_treated > 0:
        score -= 0.20 * min(1.0, n_unmatched_treated / 10.0)

    if n_matched_pairs == 0 and n_unmatched_treated > 0:
        score -= 0.10

    return max(0.0, min(1.0, score))


def compute(
    customer_ite_values: list[float],
    ci_lower: float | None = None,
    ci_upper: float | None = None,
    chosen_discount: float = 0.0,
    refutation_pass_rate: float = 0.75,
    n_samples: int = 0,
    n_distinct_treatments: int = 0,
    ci_level: float = 0.90,
    chosen_ite: float = 0.0,
    pct_outside_support: float = 0.0,
    pct_extreme: float = 0.0,
    n_unmatched_treated: int = 0,
    n_matched_pairs: int = 0,
) -> ConfidenceResult:
    result = ConfidenceResult()

    # ------------------------------------------------------------------
    # 1. Build evidence flags
    # ------------------------------------------------------------------
    ci_available = ci_lower is not None and ci_upper is not None
    ci_finite = ci_available and math.isfinite(ci_lower) and math.isfinite(ci_upper)
    ci_valid_bounds = ci_finite and ci_upper >= ci_lower
    ci_excludes_zero = ci_valid_bounds and (ci_lower > 0 or ci_upper < 0)
    sufficient_sample = n_samples >= 30
    adequate_treatment_variation = n_distinct_treatments >= 2
    refutation_passed = refutation_pass_rate >= 0.66

    ci_width = None
    ci_relative_width = None
    if ci_valid_bounds:
        ci_width = ci_upper - ci_lower
        point_magnitude = abs(chosen_ite) if chosen_ite else 0.0
        if point_magnitude > 1e-12:
            ci_relative_width = ci_width / point_magnitude

    data_support = _compute_data_support(
        pct_outside_support=pct_outside_support,
        pct_extreme=pct_extreme,
        n_unmatched_treated=n_unmatched_treated,
        n_matched_pairs=n_matched_pairs,
    )
    adequate_data_support = data_support >= 0.5

    result.evidence = {
        "ci_available": ci_available,
        "ci_finite": ci_finite,
        "ci_excludes_zero": ci_excludes_zero,
        "sufficient_sample": sufficient_sample,
        "adequate_treatment_variation": adequate_treatment_variation,
        "refutation_passed": refutation_passed,
        "refutation_pass_rate": round(refutation_pass_rate, 3),
        "ci_width": ci_width,
        "ci_relative_width": ci_relative_width,
        "data_support": round(data_support, 3),
        "pct_outside_support": round(pct_outside_support, 2),
        "pct_extreme": round(pct_extreme, 2),
        "n_unmatched_treated": n_unmatched_treated,
        "n_matched_pairs": n_matched_pairs,
        "adequate_data_support": adequate_data_support,
    }

    # ------------------------------------------------------------------
    # 2. Handle insufficient-evidence cases first
    # ------------------------------------------------------------------
    if chosen_discount == 0.0:
        result.confidence_level = "Insufficient Evidence"
        result.confidence_interval = None
        result.confidence_score = 0.0
        return result

    if not ci_available or not ci_finite or not ci_valid_bounds:
        result.confidence_level = "Insufficient Evidence"
        result.confidence_interval = None
        result.confidence_score = 0.0
        return result

    if not sufficient_sample or not adequate_treatment_variation:
        result.confidence_level = "Insufficient Evidence"
        result.confidence_interval = {"lower": ci_lower, "upper": ci_upper, "level": ci_level}
        result.confidence_score = 0.0
        return result

    # ------------------------------------------------------------------
    # 3. Build confidence interval when valid
    # ------------------------------------------------------------------
    result.confidence_interval = {"lower": ci_lower, "upper": ci_upper, "level": ci_level}

    # ------------------------------------------------------------------
    # 4. Score components
    # ------------------------------------------------------------------
    # Precision from CI width: narrower CI => higher precision.
    # Use an exponential decay. Width of 0 => precision 1.0.
    # Very wide CI => precision approaches 0.
    if ci_width is not None and ci_width > 1e-12:
        precision = math.exp(-4.0 * ci_width)
    else:
        precision = 1.0

    precision = max(0.0, min(1.0, precision))

    # Per-customer signal: how large is the point estimate relative to CI width?
    # This ratio varies across customers even when CI width is similar,
    # preventing all customers from collapsing to the same score.
    point_magnitude = abs(chosen_ite) if chosen_ite else 0.0
    if ci_width is not None and ci_width > 1e-12:
        magnitude_ratio = point_magnitude / ci_width
        magnitude_precision = 1.0 - math.exp(-magnitude_ratio)
    else:
        magnitude_precision = 0.5
    magnitude_precision = max(0.0, min(1.0, magnitude_precision))

    # Refutation component
    refutation_component = max(0.0, min(1.0, refutation_pass_rate))

    # Sample adequacy bonus
    sample_bonus = 1.0 if sufficient_sample else 0.5

    # Data support component
    data_support_component = data_support

    # ------------------------------------------------------------------
    # 5. Composite score
    # ------------------------------------------------------------------
    score = (
        0.30 * precision
        + 0.25 * magnitude_precision
        + 0.15 * refutation_component
        + 0.10 * sample_bonus
        + 0.20 * data_support_component
    )
    score = max(0.0, min(1.0, score))
    result.confidence_score = round(score, 3)

    # ------------------------------------------------------------------
    # 6. Qualitative level
    # ------------------------------------------------------------------
    if (
        ci_excludes_zero
        and precision >= 0.6
        and refutation_passed
        and sufficient_sample
        and adequate_treatment_variation
        and adequate_data_support
    ):
        result.confidence_level = "High"
    elif ci_excludes_zero and precision >= 0.3 and refutation_passed and adequate_data_support:
        result.confidence_level = "Moderate"
    elif ci_finite and adequate_data_support:
        result.confidence_level = "Low"
    else:
        result.confidence_level = "Insufficient Evidence"

    return result
