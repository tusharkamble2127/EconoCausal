"""Unit tests for the synthetic campaign EDA script."""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.eda_mock_campaign import run_eda


@pytest.fixture
def sample_dataset():
    """Create a small dataset for testing EDA."""
    return pd.DataFrame(
        {
            "tenure_months": [12, 24, 36, 48],
            "past_purchase_frequency": [1, 2, 3, 4],
            "loyalty_score": [0.1, 0.2, 0.8, 0.9],
            "avg_order_value": [20.0, 30.0, 40.0, 50.0],
            "treatment": [0.0, 0.0, 10.0, 10.0],
            "outcome": [0, 1, 1, 1],
        }
    )


def test_eda_reports_dataset_quality(tmp_path, capsys, sample_dataset):
    """EDA should report dimensions and data-quality results."""
    csv_path = tmp_path / "sample_campaign.csv"
    sample_dataset.to_csv(csv_path, index=False)

    run_eda(csv_path)

    output = capsys.readouterr().out

    assert "Rows: 4" in output
    assert "Columns: 6" in output
    assert "Missing values: 0" in output
    assert "Duplicate rows: 0" in output
    assert "EDA completed." in output


def test_eda_reports_discount_summary(
    tmp_path, capsys, sample_dataset
):
    """EDA should report purchase rates by discount level."""
    csv_path = tmp_path / "sample_campaign.csv"
    sample_dataset.to_csv(csv_path, index=False)

    run_eda(csv_path)

    output = capsys.readouterr().out

    assert "SUMMARY BY DISCOUNT LEVEL" in output
    assert "purchase_rate" in output
    assert "avg_order_value" in output
    assert "avg_loyalty" in output


def test_eda_rejects_missing_file(tmp_path):
    """EDA should raise a clear error when the file is absent."""
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        run_eda(missing_path)


def test_eda_rejects_missing_required_columns(tmp_path):
    """EDA should reject datasets missing required fields."""
    csv_path = tmp_path / "incomplete.csv"

    pd.DataFrame(
        {
            "treatment": [0, 10],
            "outcome": [0, 1],
        }
    ).to_csv(csv_path, index=False)

    with pytest.raises(
        ValueError,
        match="Dataset is missing required columns",
    ):
        run_eda(csv_path)
        