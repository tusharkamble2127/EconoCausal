"""
Exploratory Data Analysis for the synthetic campaign dataset.

Usage from the repository root:
    python scripts/eda_mock_campaign.py

To analyze another compatible CSV:
    python scripts/eda_mock_campaign.py --input data/processed/perf_test_1500.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    PROJECT_ROOT / "data" / "processed" / "mock_campaign.csv"
)

REQUIRED_COLUMNS = {
    "tenure_months",
    "past_purchase_frequency",
    "loyalty_score",
    "avg_order_value",
    "treatment",
    "outcome",
}


def run_eda(input_path: Path) -> None:
    """Load a dataset and print its quality and exploratory summaries."""

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {input_path}\n"
            "Generate the mock dataset first or provide --input."
        )

    df = pd.read_csv(input_path)

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    print("\nEXPLORATORY DATA ANALYSIS")
    print("=" * 60)
    print(f"Dataset: {input_path}")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    print("\n1. COLUMN DATA TYPES")
    print("-" * 60)
    print(df.dtypes.to_string())

    print("\n2. DATA QUALITY")
    print("-" * 60)
    print(f"Missing values: {int(df.isna().sum().sum())}")
    print(f"Duplicate rows: {int(df.duplicated().sum())}")

    print("\nMissing values by column:")
    print(df.isna().sum().to_string())

    print("\n3. NUMERICAL SUMMARY")
    print("-" * 60)
    print(df.describe().round(3).to_string())

    print("\n4. TREATMENT DISTRIBUTION")
    print("-" * 60)
    print(
        df["treatment"]
        .value_counts(dropna=False)
        .sort_index()
        .to_string()
    )

    print("\n5. OUTCOME DISTRIBUTION")
    print("-" * 60)
    print(
        df["outcome"]
        .value_counts(dropna=False)
        .sort_index()
        .to_string()
    )

    print("\n6. SUMMARY BY DISCOUNT LEVEL")
    print("-" * 60)

    grouped = df.groupby("treatment").agg(
        records=("outcome", "size"),
        purchase_rate=("outcome", "mean"),
        avg_order_value=("avg_order_value", "mean"),
        avg_loyalty=("loyalty_score", "mean"),
    )

    print(grouped.round(3).to_string())

    print("\nEDA completed.")
    print(
        "Note: These are descriptive statistics. "
        "They do not establish causal effects."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run EDA on a synthetic campaign dataset."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the input CSV file.",
    )

    args = parser.parse_args()

    try:
        run_eda(args.input)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        print(f"EDA failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())