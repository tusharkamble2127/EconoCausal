"""Unit tests for app.pipeline.cleaning (Volume II Chapter 12, Day 2)."""
import pandas as pd
import pytest

from app.core.exceptions import InsufficientTreatmentVariationError, InvalidDatasetError
from app.pipeline.cleaning import clean, validate_treatment_variation


def test_clean_removes_duplicates_and_missing_values():
    df = pd.DataFrame(
        {
            "treatment": [0.0, 0.0, 10.0, None],
            "outcome": [1, 1, 0, 1],
            "loyalty": [0.5, 0.5, 0.8, 0.2],
        }
    )
    result = clean(df)
    # One exact duplicate row removed, one row with missing treatment removed.
    assert len(result) == 2


def test_clean_raises_on_missing_required_columns():
    df = pd.DataFrame({"loyalty": [0.5, 0.8]})
    with pytest.raises(InvalidDatasetError):
        clean(df)


def test_clean_normalizes_column_names():
    df = pd.DataFrame({"Treatment": [0.0, 10.0], "Outcome": [1, 0]})
    result = clean(df)
    assert "treatment" in result.columns
    assert "outcome" in result.columns


def test_clean_uses_custom_treatment_outcome_columns():
    df = pd.DataFrame({
        "discount_given": [0.0, 10.0, None],
        "purchase_result": [1, 0, 1],
        "loyalty": [0.5, 0.8, 0.2],
    })
    result = clean(df, treatment_col="discount_given", outcome_col="purchase_result")
    assert len(result) == 2
    assert "discount_given" in result.columns
    assert "purchase_result" in result.columns


def test_validate_treatment_variation_passes_with_enough_variation():
    df = pd.DataFrame({"treatment": [0.0, 10.0, 20.0], "outcome": [1, 0, 1]})
    validate_treatment_variation(df, min_distinct=2)  # should not raise


def test_validate_treatment_variation_raises_with_single_value():
    df = pd.DataFrame({"treatment": [10.0, 10.0, 10.0], "outcome": [1, 0, 1]})
    with pytest.raises(InsufficientTreatmentVariationError):
        validate_treatment_variation(df, min_distinct=2)


def test_validate_treatment_variation_uses_custom_column():
    df = pd.DataFrame({"discount_given": [10.0, 10.0, 10.0], "outcome": [1, 0, 1]})
    with pytest.raises(InsufficientTreatmentVariationError):
        validate_treatment_variation(df, treatment_col="discount_given", min_distinct=2)


def test_clean_normalizes_custom_column_parameters():
    """Custom column names should be normalized consistently."""
    df = pd.DataFrame({
        "Discount Given": [0.0, 10.0],
        "Purchase Result": [0, 1],
        "Loyalty Score": [0.4, 0.8],
    })

    result = clean(
        df,
        treatment_col="Discount Given",
        outcome_col="Purchase Result",
    )

    assert len(result) == 2
    assert "discount_given" in result.columns
    assert "purchase_result" in result.columns
    assert "loyalty_score" in result.columns


def test_clean_removes_rows_missing_feature_values():
    """Rows with missing model features should be removed."""
    df = pd.DataFrame({
        "treatment": [0.0, 10.0, 20.0],
        "outcome": [0, 1, 1],
        "loyalty_score": [0.4, None, 0.9],
    })

    result = clean(df)

    assert len(result) == 2
    assert result["loyalty_score"].notna().all()
    assert result["treatment"].tolist() == [0.0, 20.0]


def test_clean_does_not_modify_original_dataframe():
    """Cleaning should not mutate the caller's original data."""
    df = pd.DataFrame({
        "treatment": [0.0, 10.0],
        "outcome": [0, 1],
        "loyalty_score": [0.4, None],
    })
    original = df.copy(deep=True)

    clean(df)

    pd.testing.assert_frame_equal(df, original)