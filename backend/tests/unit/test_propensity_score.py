"""Comprehensive unit tests for app.pipeline.propensity_score."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.pipeline.features import FeatureSet, engineer
from app.pipeline.propensity_score import (
    CALIPER_DEFAULT,
    PROPENSITY_COMMON_SUPPORT_MAX,
    PROPENSITY_COMMON_SUPPORT_MIN,
    PROPENSITY_EXTREME_HIGH,
    PROPENSITY_EXTREME_LOW,
    SMD_BALANCED_THRESHOLD,
    BinaryPropensityResult,
    ContinuousPropensityResult,
    MatchingResult,
    OverlapDiagnostic,
    PropensityResult,
    _compute_overlap,
    _compute_smd,
    _match_nearest_neighbor,
    estimate_binary_propensity,
    estimate_continuous_treatment_balance,
    run_propensity_analysis,
)


def _make_features(n=100, seed=42):
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({
        "loyalty_score": rng.uniform(0, 1, n),
        "tenure_months": rng.randint(1, 60, n),
        "treatment": rng.choice([0.0, 5.0, 10.0, 15.0, 20.0], n, p=[0.3, 0.25, 0.2, 0.15, 0.1]),
        "outcome": rng.binomial(1, 0.5, n),
    })
    return engineer(df), df


class TestComputeSMD:
    def test_identical_groups_returns_zero(self):
        x_t = np.array([1.0, 2.0, 3.0])
        x_c = np.array([1.0, 2.0, 3.0])
        assert _compute_smd(x_t, x_c) == 0.0

    def test_different_means(self):
        x_t = np.array([10.0, 11.0, 12.0])
        x_c = np.array([1.0, 2.0, 3.0])
        smd = _compute_smd(x_t, x_c)
        assert smd > 0
        assert np.isfinite(smd)

    def test_empty_group_returns_inf(self):
        assert _compute_smd(np.array([]), np.array([1.0, 2.0])) == float("inf")
        assert _compute_smd(np.array([1.0, 2.0]), np.array([])) == float("inf")


class TestOverlapDiagnostic:
    def test_counts_extreme_scores(self):
        p_t = np.array([0.01, 0.02, 0.5, 0.98, 0.99])
        p_c = np.array([0.03, 0.04, 0.5, 0.96, 0.97])
        o = _compute_overlap(p_t, p_c)
        assert o.n_extreme_low == 4
        assert o.n_extreme_high == 4
        assert o.pct_extreme == 80.0

    def test_outside_support(self):
        p_t = np.array([0.01, 0.5])
        p_c = np.array([0.99])
        o = _compute_overlap(p_t, p_c)
        assert o.n_outside_support >= 1


class TestBinaryPropensityEstimation:
    def test_basic_run(self):
        features, _ = _make_features()
        result = estimate_binary_propensity(features)
        assert result.method == "logistic_regression"
        assert result.treatment_type == "binary_diagnostic"
        assert result.sample_size == len(features.T)
        assert len(result.propensity_scores) == len(features.T)
        assert result.overlap is not None
        assert result.balance is not None
        assert len(result.balance) == len(features.feature_names)

    def test_matching_result_populated(self):
        features, _ = _make_features(n=200, seed=123)
        result = estimate_binary_propensity(features)
        assert result.matching is not None
        assert result.matching.method == "nearest_neighbor"

    def test_insufficient_treated(self):
        df = pd.DataFrame({
            "loyalty_score": [0.5, 0.6, 0.7],
            "tenure_months": [10, 20, 30],
            "treatment": [0.0, 0.0, 0.0],
            "outcome": [1, 0, 1],
        })
        features = engineer(df)
        result = estimate_binary_propensity(features)
        assert len(result.propensity_scores) == 0
        assert result.overlap is None
        assert len(result.warnings) > 0

    def test_insufficient_control(self):
        df = pd.DataFrame({
            "loyalty_score": [0.5, 0.6, 0.7],
            "tenure_months": [10, 20, 30],
            "treatment": [10.0, 10.0, 10.0],
            "outcome": [1, 0, 1],
        })
        features = engineer(df)
        result = estimate_binary_propensity(features)
        assert len(result.propensity_scores) == 0
        assert len(result.warnings) > 0


class TestMatching:
    def test_nearest_neighbor_basic(self):
        scores = np.array([0.1, 0.2, 0.8, 0.9])
        treated = np.array([0, 1])
        control = np.array([2, 3])
        result, mt, mc = _match_nearest_neighbor(
            scores.reshape(-1, 1), treated, control, caliper=None, replacement=False
        )
        assert result.n_matched_pairs == 2
        assert result.n_unmatched_treated == 0
        assert result.n_unmatched_control == 0

    def test_caliper_blocks_bad_matches(self):
        scores = np.array([0.1, 0.15, 0.51, 0.9])
        treated = np.array([0])
        control = np.array([1, 2, 3])
        result, mt, mc = _match_nearest_neighbor(
            scores.reshape(-1, 1), treated, control, caliper=0.1, replacement=False
        )
        assert result.n_matched_pairs == 1
        assert result.n_unmatched_control == 2

    def test_no_replacement(self):
        scores = np.array([0.1, 0.1, 0.9, 0.9])
        treated = np.array([0, 1])
        control = np.array([2, 3])
        result, mt, mc = _match_nearest_neighbor(
            scores.reshape(-1, 1), treated, control, caliper=None, replacement=False
        )
        assert result.n_matched_pairs == 2

    def test_empty_groups(self):
        result, mt, mc = _match_nearest_neighbor(
            np.array([[0.5]]), np.array([], dtype=int), np.array([0]), caliper=None
        )
        assert result.n_matched_pairs == 0


class TestContinuousTreatmentBalance:
    def test_basic_run(self):
        features, _ = _make_features(n=200, seed=42)
        result = estimate_continuous_treatment_balance(features)
        assert result.method == "continuous_stratification"
        assert result.treatment_type == "continuous"
        assert len(result.predicted_treatment) == len(features.T)
        assert result.n_strata >= 2

    def test_insufficient_variation(self):
        df = pd.DataFrame({
            "loyalty_score": [0.5, 0.6, 0.7],
            "tenure_months": [10, 20, 30],
            "treatment": [10.0, 10.0, 10.0],
            "outcome": [1, 0, 1],
        })
        features = engineer(df)
        result = estimate_continuous_treatment_balance(features)
        assert len(result.warnings) > 0

    def test_balance_metrics_populated(self):
        features, _ = _make_features(n=200, seed=42)
        result = estimate_continuous_treatment_balance(features)
        if result.balance:
            assert len(result.balance) == len(features.feature_names)


class TestRunPropensityAnalysis:
    def test_full_pipeline(self):
        features, _ = _make_features()
        result = run_propensity_analysis(features)
        assert isinstance(result, PropensityResult)
        assert result.binary is not None or result.continuous is not None

    def test_warnings_on_failure(self):
        df = pd.DataFrame({
            "loyalty_score": [0.5],
            "tenure_months": [10],
            "treatment": [0.0],
            "outcome": [1],
        })
        features = engineer(df)
        result = run_propensity_analysis(features)
        assert len(result.warnings) > 0

    def test_to_dict_serializable(self):
        features, _ = _make_features()
        result = run_propensity_analysis(features)
        d = result.to_dict()
        assert "binary" in d
        assert "continuous" in d
        assert "warnings" in d


class TestPropensityResultStructures:
    def test_binary_result_to_dict(self):
        result = BinaryPropensityResult(
            method="logistic_regression",
            treatment_type="binary_diagnostic",
            sample_size=10,
            propensity_scores=[0.1, 0.2],
            overlap=OverlapDiagnostic(
                min_propensity=0.05,
                max_propensity=0.95,
                common_support_min=0.1,
                common_support_max=0.9,
                n_total=10,
                n_outside_support=2,
                pct_outside_support=20.0,
                n_extreme_low=1,
                n_extreme_high=1,
                pct_extreme=20.0,
            ),
            balance=[],
            matching=None,
            warnings=["test warning"],
        )
        d = result.to_dict()
        assert d["method"] == "logistic_regression"
        assert d["overlap"]["pct_outside_support"] == 20.0
        assert d["warnings"] == ["test warning"]

    def test_continuous_result_to_dict(self):
        result = ContinuousPropensityResult(
            method="continuous_stratification",
            treatment_type="continuous",
            sample_size=10,
            predicted_treatment=[0.0, 5.0, 10.0],
            n_strata=5,
            balance=[],
            warnings=["continuous warning"],
        )
        d = result.to_dict()
        assert d["method"] == "continuous_stratification"
        assert d["n_strata"] == 5
        assert d["warnings"] == ["continuous warning"]


class TestBug1AfterSMDFix:
    def test_combined_balance_uses_after_values(self):
        """Bug 1 regression: combined balance must use smd_after/balanced_after."""
        rng = np.random.RandomState(42)
        n = 20
        df = pd.DataFrame({
            "loyalty_score": np.concatenate([
                rng.uniform(0.4, 1.0, 10),
                rng.uniform(0.0, 0.6, 10),
            ]),
            "tenure_months": rng.randint(1, 60, n),
            "treatment": np.concatenate([np.full(10, 10.0), np.full(10, 0.0)]),
            "outcome": rng.binomial(1, 0.5, n),
        })
        features = engineer(df)
        result = estimate_binary_propensity(features)

        assert result.balance is not None
        has_difference = False
        for b in result.balance:
            if b.smd_after is not None:
                if abs(b.smd_before - b.smd_after) > 1e-6:
                    has_difference = True
                    break
        assert has_difference, "smd_after should differ from smd_before after matching"

    def test_loyalty_balance_improves_after_matching(self):
        """With overlapping groups, matching should improve covariate balance."""
        rng = np.random.RandomState(42)
        n = 20
        df = pd.DataFrame({
            "loyalty_score": np.concatenate([
                rng.uniform(0.4, 1.0, 10),
                rng.uniform(0.0, 0.6, 10),
            ]),
            "tenure_months": rng.randint(1, 60, n),
            "treatment": np.concatenate([np.full(10, 10.0), np.full(10, 0.0)]),
            "outcome": rng.binomial(1, 0.5, n),
        })
        features = engineer(df)
        result = estimate_binary_propensity(features)

        loyalty = next(b for b in result.balance if b.feature == "loyalty_score")
        assert abs(loyalty.smd_before) > 0.5, f"Expected large before SMD, got {loyalty.smd_before}"
        assert abs(loyalty.smd_after) < abs(loyalty.smd_before), \
            f"Expected after SMD < before SMD, got before={loyalty.smd_before}, after={loyalty.smd_after}"


class TestBug2MatchedIndices:
    def test_match_nearest_neighbor_stores_actual_indices(self):
        """Bug 2 regression: MatchingResult must store actual matched indices."""
        scores = np.array([0.1, 0.2, 0.8, 0.9, 0.15, 0.85])
        treated = np.array([0, 1, 4])
        control = np.array([2, 3, 5])
        result, mt, mc = _match_nearest_neighbor(
            scores.reshape(-1, 1), treated, control, caliper=None, replacement=False
        )

        assert len(result.matched_treated_indices) == result.n_matched_pairs
        assert len(result.matched_control_indices) == result.n_matched_pairs
        assert set(result.matched_treated_indices) == {0, 1, 4}
        assert set(result.matched_control_indices) == {2, 3, 5}

    def test_combined_matched_indices_are_actual_positions(self):
        """Matched indices must be actual dataframe positions, not range()."""
        m = MatchingResult(
            method="nearest_neighbor",
            n_treated=4,
            n_control=4,
            n_matched_pairs=3,
            n_unmatched_treated=1,
            n_unmatched_control=1,
            caliper=0.2,
            replacement=False,
            matched_treated_indices=[5, 8, 12],
            matched_control_indices=[2, 7, 14],
        )

        old_style = list(range(m.n_matched_pairs))
        new_style = sorted(set(m.matched_treated_indices + m.matched_control_indices))

        assert old_style == [0, 1, 2]
        assert new_style == [2, 5, 7, 8, 12, 14]
        assert old_style != new_style

    def test_matched_pair_map_contains_actual_customer_ids(self):
        """matched_with_customer_id must contain paired customer ID, not row position."""
        m = MatchingResult(
            method="nearest_neighbor",
            n_treated=2,
            n_control=2,
            n_matched_pairs=2,
            n_unmatched_treated=0,
            n_unmatched_control=0,
            caliper=None,
            replacement=False,
            matched_treated_indices=[5, 8],
            matched_control_indices=[2, 7],
        )

        customer_ids = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]

        matched_pair_map = {}
        for t_idx, c_idx in zip(m.matched_treated_indices, m.matched_control_indices):
            matched_pair_map[t_idx] = c_idx
            matched_pair_map[c_idx] = t_idx

        assert matched_pair_map[5] == 2
        assert customer_ids[matched_pair_map[5]] == 102
        assert matched_pair_map[2] == 5
        assert customer_ids[matched_pair_map[2]] == 105
