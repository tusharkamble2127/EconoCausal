"""
Data cleaning stage (Volume I Chapter 8.2, Volume II Chapter 12 Day 2).

Owned by Member 1 (Causal Modeling Engineer, Volume II Chapter 4.1).

Responsibilities:
  - Normalize column names.
  - Remove duplicate customer records.
  - Drop rows with a missing treatment or outcome value (these cannot be
    used for causal estimation).
"""
from __future__ import annotations

import pandas as pd

from app.core.exceptions import InvalidDatasetError
from app.core.logging import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = {"treatment", "outcome"}


def clean(df: pd.DataFrame, treatment_col: str = "treatment", outcome_col: str = "outcome") -> pd.DataFrame:
    """Clean a raw historical campaign dataset.

    Args:
        df: Raw DataFrame with at least a treatment and outcome column,
            plus arbitrary confounder columns.
        treatment_col: Name of the treatment column in df.
        outcome_col: Name of the outcome column in df.

    Returns:
        A cleaned DataFrame with duplicates removed and no missing
        treatment/outcome values.

    Raises:
        InvalidDatasetError: if required columns are missing.
    """
    logger.info("Cleaning stage started: %d rows", len(df))

    df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_"))

    missing_cols = {treatment_col, outcome_col} - set(df.columns)
    if missing_cols:
        raise InvalidDatasetError(f"Dataset is missing required columns: {sorted(missing_cols)}")

    before = len(df)
    df = df.drop_duplicates()
    df = df.dropna(subset=[treatment_col, outcome_col])
    after = len(df)

    logger.info("Cleaning stage completed: %d -> %d rows (%d removed)", before, after, before - after)
    return df.reset_index(drop=True)


def validate_treatment_variation(df: pd.DataFrame, treatment_col: str = "treatment", min_distinct: int = 2) -> None:
    """Raise if the treatment column does not have enough variation to
    support causal estimation."""
    from app.core.exceptions import InsufficientTreatmentVariationError

    n_distinct = df[treatment_col].nunique()
    if n_distinct < min_distinct:
        raise InsufficientTreatmentVariationError(
            f"Treatment column has only {n_distinct} distinct value(s); "
            f"at least {min_distinct} are required for causal estimation."
        )
