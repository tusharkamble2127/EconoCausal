"""
Feature engineering stage.

Owned by Member 1 (Causal Modeling Engineer).

Splits a cleaned DataFrame into:
- X: Confounders/features
- T: Treatment
- Y: Outcome
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)

NON_FEATURE_COLUMNS = {
    "treatment",
    "outcome",
    "customer_id",
    "dataset_id",
}


def _normalize_column_name(name: object) -> str:
    """Normalize column names consistently across preprocessing stages."""
    return str(name).strip().lower().replace(" ", "_")


@dataclass
class FeatureSet:
    X: pd.DataFrame
    T: np.ndarray
    Y: np.ndarray
    feature_names: list


def engineer(
    df: pd.DataFrame,
    treatment_col: str = "treatment",
    outcome_col: str = "outcome",
) -> FeatureSet:
    """
    Split a DataFrame into confounders (X), treatment (T), and outcome (Y).

    Normalizes column names, excludes treatment/outcome and ID columns
    from X, and one-hot encodes categorical confounders.
    """
    logger.info("Feature engineering started: %d rows", len(df))

    # Work on a copy to avoid modifying the caller's DataFrame.
    df = df.copy()

    # Use the same naming convention as the cleaning pipeline.
    df = df.rename(columns=_normalize_column_name)
    treatment_col = _normalize_column_name(treatment_col)
    outcome_col = _normalize_column_name(outcome_col)

    # Validate the required treatment and outcome columns.
    missing_columns = {treatment_col, outcome_col} - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # Select confounders without leaking treatment, outcome, or IDs.
    feature_cols = [
        column
        for column in df.columns
        if column not in NON_FEATURE_COLUMNS
        and column not in {treatment_col, outcome_col}
    ]

    if not feature_cols:
        raise ValueError(
            "No confounder columns found after excluding "
            "treatment/outcome/ID columns."
        )

    X = df[feature_cols].copy()

    # Convert categorical confounders into numeric columns.
    X = pd.get_dummies(X, drop_first=True)

    T = df[treatment_col].to_numpy(dtype=float)
    Y = df[outcome_col].to_numpy(dtype=float)

    # Verify that treatment and outcome have not leaked into X.
    assert treatment_col not in X.columns, "Treatment leakage detected in X."
    assert outcome_col not in X.columns, "Outcome leakage detected in X."

    logger.info(
        "Feature engineering completed: %d confounder columns",
        X.shape[1],
    )

    return FeatureSet(
        X=X,
        T=T,
        Y=Y,
        feature_names=list(X.columns),
    )