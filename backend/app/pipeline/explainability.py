"""
Model explainability helpers (Enhancement #7).

Rather than reaching into EconML's internal nuisance models (whose
attributes vary across versions), we fit a small, purely-interpretive
RandomForestRegressor on the same X -> Y relationship to surface global
feature importances and per-customer contributing factors. This is not
used for any prediction that reaches the optimizer -- it exists solely to
explain the causal pipeline's recommendations to end users.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.core.logging import get_logger

logger = get_logger(__name__)


def compute_feature_importance(X: pd.DataFrame, Y: np.ndarray) -> Dict[str, float]:
    """Fit a small RandomForestRegressor and return normalized feature
    importances (sums to 1.0)."""
    if X.shape[1] == 0 or len(Y) == 0:
        return {}
    model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    model.fit(X.to_numpy(), Y)
    importances = model.feature_importances_
    total = importances.sum() or 1.0
    return {col: float(val / total) for col, val in zip(X.columns, importances)}


def top_contributing_factors(
    feature_row: pd.Series,
    feature_means: pd.Series,
    feature_stds: pd.Series,
    importances: Dict[str, float],
    top_n: int = 3,
) -> List[dict]:
    """Rank a single customer's features by |z-score| * global importance,
    to approximate "what pushed this recommendation".
    """
    scored = []
    for feature, value in feature_row.items():
        std = feature_stds.get(feature, 0.0) or 1.0
        mean = feature_means.get(feature, 0.0)
        z = (value - mean) / std
        importance = importances.get(feature, 0.0)
        impact = float(z * importance)
        scored.append({"feature": feature, "value": float(value), "impact": impact})

    scored.sort(key=lambda item: abs(item["impact"]), reverse=True)
    return scored[:top_n]
