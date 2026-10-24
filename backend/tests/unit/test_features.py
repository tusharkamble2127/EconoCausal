"""Unit tests for app.pipeline.features (Volume II Chapter 12, Day 3)."""
import pandas as pd

from app.pipeline.features import engineer


def test_engineer_splits_x_t_y_without_leakage():
    df = pd.DataFrame(
        {
            "treatment": [0.0, 10.0, 20.0],
            "outcome": [1, 0, 1],
            "loyalty_score": [0.5, 0.8, 0.2],
            "tenure_months": [10, 20, 30],
        }
    )
    fs = engineer(df)

    assert len(fs.X) == len(df)
    assert "treatment" not in fs.X.columns
    assert "outcome" not in fs.X.columns
    assert list(fs.T) == [0.0, 10.0, 20.0]
    assert list(fs.Y) == [1.0, 0.0, 1.0]


def test_engineer_one_hot_encodes_categoricals():
    df = pd.DataFrame(
        {
            "treatment": [0.0, 10.0],
            "outcome": [1, 0],
            "segment": ["gold", "silver"],
        }
    )
    fs = engineer(df)
    # One-hot encoding with drop_first=True should produce numeric columns only.
    assert all(fs.X.dtypes.apply(lambda d: d.kind in "biuf"))


def test_engineer_uses_custom_treatment_outcome_columns():
    df = pd.DataFrame({
        "discount_given": [0.0, 10.0, 20.0],
        "purchase_result": [1, 0, 1],
        "loyalty_score": [0.5, 0.8, 0.2],
    })
    fs = engineer(df, treatment_col="discount_given", outcome_col="purchase_result")

    assert len(fs.X) == len(df)
    assert "discount_given" not in fs.X.columns
    assert "purchase_result" not in fs.X.columns
    assert list(fs.T) == [0.0, 10.0, 20.0]
    assert list(fs.Y) == [1.0, 0.0, 1.0]
def test_engineer_normalizes_custom_column_parameters():
    """Custom treatment and outcome names should work after normalization."""
    df = pd.DataFrame({
        "Discount Given": [0.0, 10.0, 20.0],
        "Purchase Result": [0, 1, 1],
        "Loyalty Score": [0.4, 0.8, 0.9],
    })

    features = engineer(
        df,
        treatment_col="Discount Given",
        outcome_col="Purchase Result",
    )

    # Treatment and outcome should be extracted correctly.
    assert features.T.tolist() == [0.0, 10.0, 20.0]
    assert features.Y.tolist() == [0.0, 1.0, 1.0]

    # Only the actual confounder should remain in X.
    assert features.X.columns.tolist() == ["loyalty_score"]

    # Neither treatment nor outcome may leak into the feature matrix.
    assert "discount_given" not in features.X.columns
    assert "purchase_result" not in features.X.columns