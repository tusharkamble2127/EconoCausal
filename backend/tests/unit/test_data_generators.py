"""Unit tests for the synthetic dataset generators."""

import sys
from pathlib import Path

import pandas as pd

# Make the repository root importable during testing.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.generators.generate_mock_data import (
    generate as generate_mock_data,
)
from data.generators.generate_perf_test import (
    generate as generate_perf_test,
)


MOCK_COLUMNS = [
    "tenure_months",
    "past_purchase_frequency",
    "loyalty_score",
    "avg_order_value",
    "treatment",
    "outcome",
]

PERFORMANCE_COLUMNS = [
    "customer_id",
    "tenure_months",
    "past_purchase_frequency",
    "loyalty_score",
    "avg_order_value",
    "treatment",
    "outcome",
]


def test_mock_generator_is_reproducible():
    """The same seed must produce the same dataset."""
    first = generate_mock_data(100, seed=42)
    second = generate_mock_data(100, seed=42)

    pd.testing.assert_frame_equal(first, second)


def test_mock_generator_has_valid_schema_and_values():
    """Check the mock dataset's structure and valid values."""
    df = generate_mock_data(300, seed=42)

    assert df.shape == (300, 6)
    assert list(df.columns) == MOCK_COLUMNS
    assert not df.isna().any().any()
    assert df["treatment"].isin([0.0, 10.0, 20.0]).all()
    assert df["outcome"].isin([0, 1]).all()


def test_performance_generator_is_reproducible():
    """The performance generator must be reproducible."""
    first = generate_perf_test(100, seed=42)
    second = generate_perf_test(100, seed=42)

    pd.testing.assert_frame_equal(first, second)


def test_performance_generator_has_valid_schema_and_values():
    """Check performance data structure and customer identifiers."""
    df = generate_perf_test(300, seed=42)

    assert df.shape == (300, 7)
    assert list(df.columns) == PERFORMANCE_COLUMNS
    assert not df.isna().any().any()

    assert df["customer_id"].is_unique
    assert df["customer_id"].tolist() == list(range(1, 301))

    valid_treatments = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]

    assert df["treatment"].isin(valid_treatments).all()
    assert df["outcome"].isin([0, 1]).all()