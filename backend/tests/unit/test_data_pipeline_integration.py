"""Integration tests for Member 1's data-preparation pipeline."""

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.cleaning import clean, validate_treatment_variation
from app.pipeline.features import engineer
from data.generators.generate_mock_data import (
    generate as generate_mock_data,
)
from data.generators.generate_perf_test import (
    generate as generate_perf_test,
)


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(generate_mock_data, id="mock-campaign"),
        pytest.param(generate_perf_test, id="performance-dataset"),
    ],
)
def test_generated_dataset_completes_member1_pipeline(generator):
    """Generated data should pass through cleaning and feature preparation."""

    # Stage 1: Generate a reproducible dataset.
    raw = generator(200, seed=42)

    assert len(raw) == 200

    # Stage 2: Clean the dataset.
    cleaned = clean(raw)

    assert len(cleaned) > 0
    assert not cleaned.isna().any().any()
    assert not cleaned.duplicated().any()

    # Stage 3: Validate treatment variation.
    validate_treatment_variation(cleaned)

    assert cleaned["treatment"].nunique() >= 2

    # Stage 4: Prepare features, treatment, and outcome.
    features = engineer(cleaned)

    assert features.X.shape[0] == len(cleaned)
    assert features.X.shape[1] > 0
    assert features.T.shape == (len(cleaned),)
    assert features.Y.shape == (len(cleaned),)

    # Check that model inputs contain only finite numeric values.
    assert np.isfinite(features.X.to_numpy(dtype=float)).all()
    assert np.isfinite(features.T).all()
    assert np.isfinite(features.Y).all()

    # Treatment and outcome must not leak into the feature matrix.
    assert "treatment" not in features.X.columns
    assert "outcome" not in features.X.columns