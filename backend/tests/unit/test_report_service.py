"""Unit tests for report_service confidence inclusion."""
from __future__ import annotations

import csv
import io

import pytest


class _MockRun:
    status = "complete"
    run_id = 1
    campaign_name = "Test Campaign"
    budget = 100.0
    budget_used = 50.0
    budget_utilization_pct = 50.0
    customers_targeted = 10
    customers_total = 20
    average_discount = 10.0
    estimated_uplift = 0.5
    incremental_revenue = 100.0
    roi_improvement_pct = 10.0
    savings_vs_blanket = 20.0


class _MockAllocation:
    customer_id = 1
    chosen_discount = 10.0
    budget_used = 10.0


class _MockIteScore:
    def __init__(self, customer_id: int, discount_level: float, ite_value: float, ci_lower: float, ci_upper: float):
        self.customer_id = customer_id
        self.discount_level = discount_level
        self.ite_value = ite_value
        self.ci_lower = ci_lower
        self.ci_upper = ci_upper


class _MockRefutation:
    passed = True


class _MockPropensityDiagnostic:
    metric_name = "overlap_summary"
    details_json = '{"pct_outside_support": 5.0, "pct_extreme": 3.0, "n_total": 30, "n_outside_support": 1, "n_extreme_low": 0, "n_extreme_high": 1}'


def _make_ite_scores():
    levels = [0.0, 10.0, 20.0]
    scores = []
    for i in range(30):
        level = levels[i % 3]
        ite = 0.05 * (level / 10.0)
        scores.append(_MockIteScore(1, level, ite, ite - 0.01, ite + 0.01))
    return scores


def test_generate_csv_includes_confidence(monkeypatch):
    from app.services import report_service

    def mock_run_get(db_session, run_id):
        return _MockRun()

    def mock_alloc_list(db_session, run_id):
        return [_MockAllocation()]

    def mock_ite_list(db_session, run_id):
        return _make_ite_scores()

    def mock_ref_list(db_session, run_id):
        return [_MockRefutation()]

    def mock_prop_diag_list(db_session, run_id):
        return [_MockPropensityDiagnostic()]

    monkeypatch.setattr(report_service.run_repository, "get", mock_run_get)
    monkeypatch.setattr(report_service.allocation_repository, "list_by_run", mock_alloc_list)
    monkeypatch.setattr(report_service.ite_repository, "list_by_run", mock_ite_list)
    monkeypatch.setattr(report_service.refutation_repository, "list_by_run", mock_ref_list)
    monkeypatch.setattr(report_service.propensity_diagnostic_repository, "list_by_run", mock_prop_diag_list)

    csv_bytes = report_service.generate_csv({}, 1)
    text = csv_bytes.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["customer_id", "chosen_discount", "budget_used", "confidence_score", "confidence_level"]
    assert len(rows) == 2
    score = float(rows[1][3])
    level = rows[1][4]
    assert 0.0 <= score <= 1.0
    assert level in ("High", "Moderate", "Low", "Insufficient Evidence")


def test_generate_pdf_includes_confidence(monkeypatch):
    from app.services import report_service

    def mock_run_get(db_session, run_id):
        return _MockRun()

    def mock_alloc_list(db_session, run_id):
        return [_MockAllocation()]

    def mock_ite_list(db_session, run_id):
        return _make_ite_scores()

    def mock_ref_list(db_session, run_id):
        return [_MockRefutation()]

    def mock_prop_diag_list(db_session, run_id):
        return [_MockPropensityDiagnostic()]

    def mock_summary_get(db_session, run_id):
        return _MockRun()

    monkeypatch.setattr(report_service.run_repository, "get", mock_run_get)
    monkeypatch.setattr(report_service.allocation_repository, "list_by_run", mock_alloc_list)
    monkeypatch.setattr(report_service.ite_repository, "list_by_run", mock_ite_list)
    monkeypatch.setattr(report_service.refutation_repository, "list_by_run", mock_ref_list)
    monkeypatch.setattr(report_service.propensity_diagnostic_repository, "list_by_run", mock_prop_diag_list)
    monkeypatch.setattr(report_service.summary_service, "get_summary", mock_summary_get)

    pdf_bytes = report_service.generate_pdf({}, 1)
    assert pdf_bytes.startswith(b"%PDF")
