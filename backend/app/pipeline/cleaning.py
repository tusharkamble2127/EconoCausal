"""
Data cleaning stage.

Responsibilities:
- Normalize column names.
- Remove duplicate records.
- Remove rows with missing treatment or outcome values.
- Remove rows with missing model-feature values.
"""

from __future__ import annotations

import pandas as pd

from app.core.exceptions import (
    InsufficientTreatmentVariationError,
    InvalidDatasetError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

NON_FEATURE_COLUMNS = {
    "treatment",
    "outcome",
    "customer_id",
    "dataset_id",
}


def _normalize_column_name(name: object) -> str:
    """Normalize a column name consistently."""
    return str(name).strip().lower().replace(" ", "_")


def clean(
    df: pd.DataFrame,
    treatment_col: str = "treatment",
    outcome_col: str = "outcome",
) -> pd.DataFrame:
    """
    Clean a dataset for causal analysis.

    Normalizes column names, removes duplicate rows, and removes
    observations missing treatment, outcome, or model-feature values.

    Optional identifier columns such as customer_id and dataset_id
    are excluded from the model-feature completeness check.
    """
    original_rows = len(df)

    logger.info(
        "Cleaning stage started: %d rows",
        original_rows,
    )

    # Work on a copy so the caller's original DataFrame is unchanged.
    df = df.copy()

    # Normalize DataFrame columns and parameter names consistently.
    df = df.rename(columns=_normalize_column_name)

    treatment_col = _normalize_column_name(treatment_col)
    outcome_col = _normalize_column_name(outcome_col)

    missing_cols = {treatment_col, outcome_col} - set(df.columns)

    if missing_cols:
        raise InvalidDatasetError(
            f"Dataset is missing required columns: {sorted(missing_cols)}"
        )

    # Stage 1: Remove duplicate records.
    before_duplicates = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before_duplicates - len(df)

    # Stage 2: Remove rows without treatment or outcome.
    before_targets = len(df)
    df = df.dropna(subset=[treatment_col, outcome_col])
    missing_targets_removed = before_targets - len(df)

    # Stage 3: Remove rows missing any model-feature value.
    # ID columns are not model features and are excluded.
    feature_cols = [
        column
        for column in df.columns
        if column not in NON_FEATURE_COLUMNS
        and column not in {treatment_col, outcome_col}
    ]

    before_features = len(df)

    if feature_cols:
        df = df.dropna(subset=feature_cols)

    missing_features_removed = before_features - len(df)

    df = df.reset_index(drop=True)

    logger.info(
        "Cleaning completed: %d -> %d rows; "
        "duplicates=%d, missing_targets=%d, missing_features=%d",
        original_rows,
        len(df),
        duplicates_removed,
        missing_targets_removed,
        missing_features_removed,
    )

    return df


def validate_treatment_variation(
    df: pd.DataFrame,
    treatment_col: str = "treatment",
    min_distinct: int = 2,
) -> None:
    """Ensure the treatment column has sufficient variation."""
    treatment_col = _normalize_column_name(treatment_col)

    if treatment_col not in df.columns:
        raise InvalidDatasetError(
            f"Dataset is missing treatment column: {treatment_col}"
        )

    if min_distinct < 1:
        raise ValueError("min_distinct must be at least 1.")

    n_distinct = df[treatment_col].nunique()

    if n_distinct < min_distinct:
        raise InsufficientTreatmentVariationError(
            f"Treatment column has only {n_distinct} distinct value(s); "
            f"at least {min_distinct} are required for causal estimation."
        )