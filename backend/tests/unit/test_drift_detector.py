"""Unit tests for app.pipeline.drift_detector (Volume II Chapter 12, Day 24)."""
import numpy as np
import pandas as pd

from app.pipeline.drift_detector import any_drift, detect_drift


def test_detect_drift_flags_a_shifted_distribution():
    rng = np.random.default_rng(0)
    training = pd.DataFrame({"loyalty_score": rng.uniform(0, 1, 500)})
    shifted = pd.DataFrame({"loyalty_score": rng.uniform(0, 1, 500) + 0.6})

    reports = detect_drift(training, shifted, p_value_threshold=0.05)
    assert any_drift(reports) is True
    assert reports[0].feature == "loyalty_score"
    assert reports[0].drifted is True


def test_detect_drift_does_not_flag_identical_distribution():
    rng = np.random.default_rng(1)
    training = pd.DataFrame({"tenure_months": rng.uniform(0, 60, 1000)})
    same = pd.DataFrame({"tenure_months": rng.uniform(0, 60, 1000)})

    reports = detect_drift(training, same, p_value_threshold=0.01)
    assert any_drift(reports) is False
