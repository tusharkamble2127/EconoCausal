"""
Automated data drift detector (Volume I Chapter 10 Day 24,
Volume II Chapter 11.9, Chapter 12 Day 24).

Owned by Member 2 (ML & Optimization Engineer, Volume II Chapter 4.2).

Uses a simple, explainable statistical-distance approach (a two-sample
Kolmogorov-Smirnov test per numeric confounder) rather than a black-box
drift model, so the result can be explained plainly at Final Review
(Volume II Chapter 11.9).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
from scipy.stats import ks_2samp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DriftReport:
    feature: str
    p_value: float
    drifted: bool


def detect_drift(
    training_X: pd.DataFrame,
    incoming_X: pd.DataFrame,
    p_value_threshold: float = None,
) -> List[DriftReport]:
    """Compare each numeric confounder's distribution between the training
    dataset and newly submitted data.

    A feature is flagged as drifted if the KS test's p-value falls below
    the threshold (default from app.core.config), meaning the two samples
    are unlikely to come from the same distribution.
    """
    threshold = p_value_threshold if p_value_threshold is not None else settings.drift_p_value_threshold
    reports: List[DriftReport] = []

    common_cols = [c for c in training_X.columns if c in incoming_X.columns]
    for col in common_cols:
        try:
            statistic, p_value = ks_2samp(
                training_X[col].dropna().to_numpy(),
                incoming_X[col].dropna().to_numpy(),
            )
        except Exception as exc:  # pragma: no cover - defensive, logged for audit
            logger.error("Drift test failed for column %s: %s", col, exc)
            continue

        drifted = bool(p_value < threshold)
        reports.append(DriftReport(feature=col, p_value=float(p_value), drifted=drifted))
        if drifted:
            logger.info("Drift detected in feature '%s' (p=%.4f < %.2f)", col, p_value, threshold)

    return reports


def any_drift(reports: List[DriftReport]) -> bool:
    return any(r.drifted for r in reports)
