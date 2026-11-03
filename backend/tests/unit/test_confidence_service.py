"""Unit tests for the canonical confidence service."""
from __future__ import annotations

import math

import pytest

from app.services.confidence_service import compute, ConfidenceResult


class TestConfidenceBaseline:
    def test_zero_discount_returns_insufficient_evidence(self):
        result = compute([], chosen_discount=0.0)
        assert result.confidence_level == "Insufficient Evidence"
        assert result.confidence_score == 0.0
        assert result.confidence_interval is None

    def test_zero_discount_with_nonzero_ites(self):
        result = compute([0.1, 0.2, 0.3], chosen_discount=0.0)
        assert result.confidence_level == "Insufficient Evidence"
        assert result.confidence_score == 0.0


class TestConfidenceMissingCi:
    def test_missing_ci_returns_insufficient_evidence(self):
        result = compute([0.1, 0.2], chosen_discount=10.0, ci_lower=None, ci_upper=None)
        assert result.confidence_level == "Insufficient Evidence"
        assert result.confidence_score == 0.0
        assert result.confidence_interval is None

    def test_nan_ci_returns_insufficient_evidence(self):
        result = compute([0.1], chosen_discount=10.0, ci_lower=float("nan"), ci_upper=0.2)
        assert result.confidence_level == "Insufficient Evidence"

    def test_infinite_ci_returns_insufficient_evidence(self):
        result = compute([0.1], chosen_discount=10.0, ci_lower=float("-inf"), ci_upper=float("inf"))
        assert result.confidence_level == "Insufficient Evidence"

    def test_reversed_ci_bounds_returns_insufficient_evidence(self):
        result = compute([0.1], chosen_discount=10.0, ci_lower=0.3, ci_upper=0.1)
        assert result.confidence_level == "Insufficient Evidence"


class TestConfidenceSampleSize:
    def test_tiny_sample_returns_insufficient_evidence(self):
        result = compute(
            [0.1],
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=5,
            n_distinct_treatments=3,
        )
        assert result.confidence_level == "Insufficient Evidence"

    def test_sufficient_sample_with_valid_ci(self):
        result = compute(
            [0.1] * 30,
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=30,
            n_distinct_treatments=3,
        )
        assert result.confidence_level in ("High", "Moderate", "Low")
        assert 0.0 <= result.confidence_score <= 1.0


class TestConfidenceTreatmentVariation:
    def test_insufficient_treatment_variation_returns_insufficient_evidence(self):
        result = compute(
            [0.1],
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=50,
            n_distinct_treatments=1,
        )
        assert result.confidence_level == "Insufficient Evidence"

    def test_adequate_treatment_variation(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=50,
            n_distinct_treatments=3,
        )
        assert result.confidence_level != "Insufficient Evidence"


class TestConfidenceCiExcludesZero:
    def test_ci_excluding_zero_can_achieve_high(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.confidence_level == "High"
        assert result.confidence_interval is not None
        assert result.confidence_interval["lower"] == 0.08
        assert result.confidence_interval["upper"] == 0.12

    def test_ci_crossing_zero(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.confidence_level in ("Low", "Moderate")
        assert not result.evidence["ci_excludes_zero"]


class TestConfidenceWideCi:
    def test_wide_ci_lowers_confidence(self):
        narrow = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        wide = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.5,
            ci_upper=0.7,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert narrow.confidence_score > wide.confidence_score


class TestConfidenceRefutation:
    def test_failed_refutation_lowers_confidence(self):
        strong = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        weak = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=0.3,
        )
        assert strong.confidence_score > weak.confidence_score


class TestConfidenceScoreBounds:
    def test_score_always_between_zero_and_one(self):
        for discount in [5.0, 10.0, 15.0, 20.0]:
            for n_samples in [5, 30, 100]:
                for n_treatments in [1, 2, 5]:
                    result = compute(
                        [0.1] * max(1, n_samples),
                        chosen_discount=discount,
                        ci_lower=0.01 if n_samples >= 30 else None,
                        ci_upper=0.19 if n_samples >= 30 else None,
                        n_samples=n_samples,
                        n_distinct_treatments=n_treatments,
                    )
                    assert 0.0 <= result.confidence_score <= 1.0

    def test_score_varies_with_evidence(self):
        r1 = compute([0.1] * 50, chosen_discount=10.0, ci_lower=0.05, ci_upper=0.15, n_samples=50, n_distinct_treatments=3)
        r2 = compute([0.1] * 50, chosen_discount=10.0, ci_lower=-0.5, ci_upper=0.7, n_samples=50, n_distinct_treatments=3)
        assert r1.confidence_score != r2.confidence_score


class TestConfidenceEvidence:
    def test_evidence_fields_populated(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
        )
        assert "ci_available" in result.evidence
        assert "ci_finite" in result.evidence
        assert "ci_excludes_zero" in result.evidence
        assert "sufficient_sample" in result.evidence
        assert "adequate_treatment_variation" in result.evidence
        assert "refutation_passed" in result.evidence
        assert "ci_width" in result.evidence
        assert "ci_relative_width" in result.evidence

    def test_evidence_ci_width(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
        )
        assert result.evidence["ci_width"] == 0.16


class TestConfidenceBackwardCompatibility:
    def test_legacy_call_signature_still_works(self):
        result = compute([0.1, 0.2], ci_lower=0.05, ci_upper=0.15, chosen_discount=10.0, refutation_pass_rate=0.8)
        assert isinstance(result, ConfidenceResult)
        assert hasattr(result, "confidence_score")
        assert hasattr(result, "confidence_level")


class TestConfidenceDataSupport:
    def test_good_overlap_achieves_high(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
        )
        assert result.confidence_level == "High"

    def test_poor_overlap_lowers_confidence(self):
        good = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
        )
        poor = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=45.0,
            pct_extreme=25.0,
            n_unmatched_treated=15,
            n_matched_pairs=0,
        )
        assert good.confidence_score > poor.confidence_score

    def test_extreme_propensity_penalizes(self):
        good = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_extreme=3.0,
        )
        extreme = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_extreme=25.0,
        )
        assert good.confidence_score > extreme.confidence_score

    def test_unmatched_treated_penalizes(self):
        good = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
        )
        unmatched = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            n_unmatched_treated=20,
            n_matched_pairs=0,
        )
        assert good.confidence_score > unmatched.confidence_score

    def test_data_support_evidence_populated(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            pct_outside_support=12.0,
            pct_extreme=5.0,
            n_unmatched_treated=2,
            n_matched_pairs=35,
        )
        assert "data_support" in result.evidence
        assert "pct_outside_support" in result.evidence
        assert "pct_extreme" in result.evidence
        assert "n_unmatched_treated" in result.evidence
        assert "n_matched_pairs" in result.evidence
        assert "adequate_data_support" in result.evidence


class TestConfidenceEvidenceConsistency:
    def test_ci_relative_width_uses_chosen_ite(self):
        result = compute(
            [0.5, 0.6, 0.7],
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
            chosen_ite=0.15,
        )
        ci_relative_width = result.evidence["ci_relative_width"]
        ci_width = result.evidence["ci_width"]
        assert ci_relative_width == ci_width / 0.15

    def test_evidence_snr_and_ci_refer_to_same_effect(self):
        chosen = 0.12
        result = compute(
            [0.5, 0.6, 0.7],
            chosen_discount=10.0,
            ci_lower=0.02,
            ci_upper=0.18,
            n_samples=50,
            n_distinct_treatments=3,
            chosen_ite=chosen,
        )
        ci_relative_width = result.evidence["ci_relative_width"]
        ci_width = result.evidence["ci_width"]
        assert ci_relative_width == pytest.approx(ci_width / chosen)


class TestConfidenceCiWidthScale:
    def test_narrow_ci_yields_high_precision(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.09,
            ci_upper=0.11,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.evidence["ci_width"] == pytest.approx(0.02)
        assert result.confidence_score > 0.5

    def test_medium_ci_yields_moderate_precision(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.evidence["ci_width"] == pytest.approx(0.10)

    def test_wide_ci_yields_low_precision(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.5,
            ci_upper=0.7,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.evidence["ci_width"] == 1.2
        assert result.confidence_score < 0.5

    def test_zero_width_ci_yields_max_precision(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.10,
            ci_upper=0.10,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.evidence["ci_width"] == 0.0
        assert result.confidence_score > 0.5

    def test_boundary_ci_within_unit_interval(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.0,
            ci_upper=1.0,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.evidence["ci_width"] == 1.0
        assert 0.0 <= result.confidence_score <= 1.0


class TestConfidenceDataSupportOverlap:
    def test_overlapping_failures_are_penalized(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=45.0,
            pct_extreme=25.0,
            n_unmatched_treated=15,
            n_matched_pairs=0,
        )
        assert result.evidence["data_support"] < 0.5
        assert result.confidence_level in ("Low", "Insufficient Evidence")

    def test_isolated_extreme_propensity_penalizes(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_extreme=25.0,
        )
        assert result.evidence["data_support"] < 1.0

    def test_isolated_unmatched_treated_penalizes(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            n_unmatched_treated=20,
            n_matched_pairs=0,
        )
        assert result.evidence["data_support"] < 1.0


class TestConfidenceMissingRefutation:
    def test_missing_refutation_uses_heuristic_fallback(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=0.75,
        )
        assert result.evidence["refutation_pass_rate"] == 0.75

    def test_missing_refutation_does_not_reach_maximum(self):
        best_evidence = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
        )
        heuristic_evidence = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=0.75,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
        )
        assert best_evidence.confidence_score > heuristic_evidence.confidence_score


class TestConfidenceSampleSizeHeuristic:
    def test_tiny_sample_returns_insufficient_evidence(self):
        result = compute(
            [0.1],
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=5,
            n_distinct_treatments=3,
        )
        assert result.confidence_level == "Insufficient Evidence"
        assert result.evidence["sufficient_sample"] is False

    def test_exactly_thirty_samples_can_produce_score(self):
        result = compute(
            [0.1] * 30,
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=30,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
        )
        assert result.confidence_level in ("High", "Moderate", "Low")
        assert result.evidence["sufficient_sample"] is True

    def test_large_sample_remains_heuristic(self):
        result = compute(
            [0.1] * 1000,
            chosen_discount=10.0,
            ci_lower=0.05,
            ci_upper=0.15,
            n_samples=1000,
            n_distinct_treatments=3,
        )
        assert result.evidence["sufficient_sample"] is True
        assert 0.0 <= result.confidence_score <= 1.0


class TestConfidenceScoreSemantics:
    def test_large_effect_narrow_ci_high_reliability(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
            chosen_ite=0.5,
        )
        assert result.confidence_level == "High"

    def test_large_effect_wide_ci_low_reliability(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.5,
            ci_upper=0.7,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
            chosen_ite=0.5,
        )
        assert result.confidence_score < 0.6

    def test_small_effect_narrow_ci_moderate_reliability(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.09,
            ci_upper=0.11,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
            chosen_ite=0.02,
        )
        assert result.confidence_score >= 0.3

    def test_missing_evidence_does_not_reach_maximum(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=0.75,
            pct_outside_support=45.0,
            pct_extreme=25.0,
            n_unmatched_treated=15,
            n_matched_pairs=0,
        )
        assert result.confidence_score < 0.8

    def test_zero_effect_with_narrow_ci(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.01,
            ci_upper=0.01,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            chosen_ite=0.0,
        )
        assert result.confidence_level != "High"

    def test_negative_effect_bounded(self):
        result = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=-0.20,
            ci_upper=-0.10,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            chosen_ite=-0.15,
        )
        assert 0.0 <= result.confidence_score <= 1.0

    def test_all_scores_bounded_zero_to_one(self):
        for ci_lower, ci_upper in [
            (0.0, 0.0),
            (-1.0, 1.0),
            (0.08, 0.12),
            (float("nan"), 0.2),
            (float("-inf"), float("inf")),
            (0.3, 0.1),
        ]:
            result = compute(
                [0.1] * 50,
                chosen_discount=10.0,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                n_samples=50,
                n_distinct_treatments=3,
                chosen_ite=0.1,
            )
            assert 0.0 <= result.confidence_score <= 1.0

    def test_deterministic_repeated_execution(self):
        r1 = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
            chosen_ite=0.15,
        )
        r2 = compute(
            [0.1] * 50,
            chosen_discount=10.0,
            ci_lower=0.08,
            ci_upper=0.12,
            n_samples=50,
            n_distinct_treatments=3,
            refutation_pass_rate=1.0,
            pct_outside_support=5.0,
            pct_extreme=3.0,
            n_unmatched_treated=0,
            n_matched_pairs=40,
            chosen_ite=0.15,
        )
        assert r1.confidence_score == r2.confidence_score
        assert r1.confidence_level == r2.confidence_level
