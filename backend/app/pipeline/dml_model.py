"""
EconML Double Machine Learning training and ITE estimation
(Volume I Chapter 8.5-8.6, Volume II Chapter 12 Days 8-10).

Owned by Member 2 (ML & Optimization Engineer, Volume II Chapter 4.2).

The discount amount (treatment) is numeric (e.g., 0, 10, 20), so it is
modeled as a continuous treatment. EconML's LinearDML estimates the
effect of moving from a baseline treatment (0) to any candidate discount
level, for every customer -- this is the Individual Treatment Effect
(Volume I Chapter 1.5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import numpy as np
import pandas as pd
from econml.dml import LinearDML
from sklearn.ensemble import RandomForestRegressor

from app.core.logging import get_logger
from app.pipeline.features import FeatureSet

logger = get_logger(__name__)

BASE_ESTIMATORS = {
    "RandomForest": lambda: RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1),
}


@dataclass
class ItePrediction:
    customer_id: int
    discount_level: float
    ite_value: float
    ci_lower: float = 0.0
    ci_upper: float = 0.0


def _make_base_estimator(name: str):
    if name not in BASE_ESTIMATORS:
        raise ValueError(f"Unsupported base_estimator '{name}'. Supported: {sorted(BASE_ESTIMATORS)}")
    return BASE_ESTIMATORS[name]()


def train(features: FeatureSet, base_estimator: str = "RandomForest") -> LinearDML:
    """Train EconML's Double ML estimator on the engineered feature set."""
    logger.info("DML training started with base estimator=%s, n=%d", base_estimator, len(features.T))

    model_y = _make_base_estimator(base_estimator)
    model_t = _make_base_estimator(base_estimator)

    est = LinearDML(
        model_y=model_y,
        model_t=model_t,
        discrete_treatment=False,
        random_state=42,
    )
    est.fit(Y=features.Y, T=features.T, X=features.X.to_numpy())

    logger.info("DML training completed")
    return est


def estimate_ite(
    est: LinearDML,
    features: FeatureSet,
    customer_ids: Iterable[int],
    discount_levels: Iterable[float],
    baseline: float = 0.0,
    ci_alpha: float = 0.1,
) -> List[ItePrediction]:
    """Estimate the Individual Treatment Effect for every customer, for
    every candidate discount level, relative to a baseline (no discount).

    Also computes a (1 - ci_alpha) confidence interval per prediction.

    FORENSIC PASS NOTE: this CI is what the Customer Recommendation
    Panel's confidence_score is now based on (see
    app/services/recommendation_service.py). The previous confidence
    formula instead measured how "consistent" a customer's ITE was
    across discount levels (spread/magnitude) -- but LinearDML models
    the treatment effect as `theta(X) * dose`, a straight line through
    the origin, so the *ratio* between any two doses' ITE is identical
    for every customer by construction (e.g. ITE@10 is always exactly
    half of ITE@20, for everyone). That made the old formula collapse
    to the same constant value for the entire dataset regardless of the
    data -- confirmed via a live run where all 300 customers returned
    exactly the same confidence_score. Statistical estimation
    uncertainty (this CI), not dose-response shape, is the correct
    signal for "how confident are we in this specific estimate".
    """
    predictions: List[ItePrediction] = []
    X = features.X.to_numpy()
    customer_ids = list(customer_ids)

    for level in discount_levels:
        if level == baseline:
            effects = np.zeros(len(customer_ids))
            lowers = np.zeros(len(customer_ids))
            uppers = np.zeros(len(customer_ids))
        else:
            t0 = np.full(len(customer_ids), baseline, dtype=float)
            t1 = np.full(len(customer_ids), level, dtype=float)
            effects = est.effect(X, T0=t0, T1=t1)
            try:
                lowers, uppers = est.effect_interval(X, T0=t0, T1=t1, alpha=ci_alpha)
            except Exception:  # pragma: no cover - inference unavailable for some estimator configs
                logger.warning("effect_interval unavailable; falling back to point estimate as the interval")
                lowers, uppers = effects, effects

        for cid, effect, lo, hi in zip(customer_ids, effects, lowers, uppers):
            predictions.append(
                ItePrediction(
                    customer_id=cid,
                    discount_level=float(level),
                    ite_value=float(effect),
                    ci_lower=float(lo),
                    ci_upper=float(hi),
                )
            )

    logger.info("ITE estimation completed: %d predictions", len(predictions))
    return predictions
