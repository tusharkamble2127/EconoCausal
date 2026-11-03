"""
Feature engineering stage (Volume I Chapter 8.3, Volume II Chapter 12 Day 3).

Owned by Member 1 (Causal Modeling Engineer, Volume II Chapter 4.1).

Splits a cleaned DataFrame into the X (confounders), T (treatment), and
Y (outcome) arrays that both DoWhy and EconML expect.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)

NON_FEATURE_COLUMNS = {"treatment", "outcome", "customer_id", "dataset_id"}


@dataclass
class FeatureSet:
    X: pd.DataFrame  # confounders
    T: np.ndarray  # treatment
    Y: np.ndarray  # outcome
    feature_names: list


def engineer(df: pd.DataFrame, treatment_col: str = "treatment", outcome_col: str = "outcome") -> FeatureSet:
    """Split a cleaned DataFrame into confounders (X), treatment (T),
    and outcome (Y).

    Guarantees the treatment and outcome columns never leak into X
    (Volume II Chapter 12, Day 3 error note).
    """
    logger.info("Feature engineering started: %d rows", len(df))

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS and c not in {treatment_col, outcome_col}]
    if not feature_cols:
        raise ValueError("No confounder columns found after excluding treatment/outcome/id columns.")

    X = df[feature_cols].copy()

    # One-hot encode any categorical confounders so downstream estimators
    # (Random Forest / LightGBM) receive purely numeric input.
    X = pd.get_dummies(X, drop_first=True)

    T = df[treatment_col].to_numpy(dtype=float)
    Y = df[outcome_col].to_numpy(dtype=float)

    assert treatment_col not in X.columns and outcome_col not in X.columns, "Target leakage detected in X."

    logger.info("Feature engineering completed: %d confounder columns", X.shape[1])
    return FeatureSet(X=X, T=T, Y=Y, feature_names=list(X.columns))
