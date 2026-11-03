"""Downloadable CSV/PDF campaign reports (Phase 3, Enhancement #10)."""
from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import (
    allocation_repository,
    ite_repository,
    propensity_diagnostic_repository,
    refutation_repository,
    run_repository,
)
from app.services import summary_service
from app.services.confidence_service import compute as compute_confidence


def _extract_propensity_metrics(diagnostics) -> dict:
    pct_outside_support = 0.0
    pct_extreme = 0.0
    n_unmatched_treated = 0
    n_matched_pairs = 0
    for d in diagnostics:
        if d.metric_name == "overlap_summary" and d.details_json:
            try:
                details = json.loads(d.details_json)
                pct_outside_support = float(details.get("pct_outside_support", 0.0))
                pct_extreme = float(details.get("pct_extreme", 0.0))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        elif d.metric_name == "matching_summary" and d.details_json:
            try:
                details = json.loads(d.details_json)
                n_unmatched_treated = int(details.get("n_unmatched_treated", 0))
                n_matched_pairs = int(details.get("n_matched_pairs", 0))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    return {
        "pct_outside_support": pct_outside_support,
        "pct_extreme": pct_extreme,
        "n_unmatched_treated": n_unmatched_treated,
        "n_matched_pairs": n_matched_pairs,
    }


def generate_csv(db: Session, run_id: int) -> bytes:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Report not available until run {run_id} completes.")

    allocations = allocation_repository.list_by_run(db, run_id)
    ite_scores = ite_repository.list_by_run(db, run_id)
    refutations = refutation_repository.list_by_run(db, run_id)
    propensity_diagnostics = propensity_diagnostic_repository.list_by_run(db, run_id)
    propensity_metrics = _extract_propensity_metrics(propensity_diagnostics)

    ite_lookup = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}
    ci_lookup = {(s.customer_id, s.discount_level): (s.ci_lower, s.ci_upper) for s in ite_scores}
    pass_rate = (sum(1 for r in refutations if r.passed) / len(refutations)) if refutations else 0.75
    n_samples = len(ite_scores)
    n_distinct_treatments = len({s.discount_level for s in ite_scores})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["customer_id", "chosen_discount", "budget_used", "confidence_score", "confidence_level"])
    for a in allocations:
        customer_ite_values = [v for (cid, _lvl), v in ite_lookup.items() if cid == a.customer_id]
        chosen_ci = ci_lookup.get((a.customer_id, a.chosen_discount))
        ci_lower = chosen_ci[0] if chosen_ci else None
        ci_upper = chosen_ci[1] if chosen_ci else None
        chosen_ite = ite_lookup.get((a.customer_id, a.chosen_discount), 0.0)
        confidence_result = compute_confidence(
            customer_ite_values,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            chosen_discount=a.chosen_discount,
            refutation_pass_rate=pass_rate,
            n_samples=n_samples,
            n_distinct_treatments=n_distinct_treatments,
            chosen_ite=chosen_ite,
            pct_outside_support=propensity_metrics["pct_outside_support"],
            pct_extreme=propensity_metrics["pct_extreme"],
            n_unmatched_treated=propensity_metrics["n_unmatched_treated"],
            n_matched_pairs=propensity_metrics["n_matched_pairs"],
        )
        writer.writerow([
            a.customer_id,
            a.chosen_discount,
            a.budget_used,
            round(confidence_result.confidence_score, 3),
            confidence_result.confidence_level,
        ])
    return buffer.getvalue().encode("utf-8")


def generate_pdf(db: Session, run_id: int) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    summary = summary_service.get_summary(db, run_id)
    allocations = allocation_repository.list_by_run(db, run_id)
    ite_scores = ite_repository.list_by_run(db, run_id)
    refutations = refutation_repository.list_by_run(db, run_id)
    propensity_diagnostics = propensity_diagnostic_repository.list_by_run(db, run_id)
    propensity_metrics = _extract_propensity_metrics(propensity_diagnostics)

    ite_lookup = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}
    ci_lookup = {(s.customer_id, s.discount_level): (s.ci_lower, s.ci_upper) for s in ite_scores}
    pass_rate = (sum(1 for r in refutations if r.passed) / len(refutations)) if refutations else 0.75
    n_samples = len(ite_scores)
    n_distinct_treatments = len({s.discount_level for s in ite_scores})

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"EconoCausal Campaign Report: {summary.campaign_name}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Run #{summary.run_id}", styles["Normal"]),
        Spacer(1, 12),
    ]

    kpi_rows = [
        ["Budget", f"${summary.budget:,.2f}"],
        ["Budget Used", f"${summary.budget_used:,.2f} ({summary.budget_utilization_pct:.1f}%)"],
        ["Customers Targeted", f"{summary.customers_targeted} / {summary.customers_total}"],
        ["Average Discount", f"{summary.average_discount:,.2f}%"],
        ["Estimated Uplift", f"{summary.estimated_uplift:,.3f}"],
        ["Incremental Revenue", f"${summary.incremental_revenue:,.2f}"],
        ["ROI Improvement vs. Blanket Targeting", f"{summary.roi_improvement_pct:,.1f}%"],
        ["Savings vs. Blanket Targeting", f"${summary.savings_vs_blanket:,.2f}"],
    ]
    kpi_table = Table(kpi_rows, colWidths=[220, 220])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Allocation Detail (first 200 customers)", styles["Heading2"]))
    story.append(Spacer(1, 8))

    alloc_rows = [["Customer ID", "Chosen Discount", "Budget Used", "Confidence Score", "Confidence Level"]]
    for a in allocations[:200]:
        customer_ite_values = [v for (cid, _lvl), v in ite_lookup.items() if cid == a.customer_id]
        chosen_ci = ci_lookup.get((a.customer_id, a.chosen_discount))
        ci_lower = chosen_ci[0] if chosen_ci else None
        ci_upper = chosen_ci[1] if chosen_ci else None
        chosen_ite = ite_lookup.get((a.customer_id, a.chosen_discount), 0.0)
        confidence_result = compute_confidence(
            customer_ite_values,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            chosen_discount=a.chosen_discount,
            refutation_pass_rate=pass_rate,
            n_samples=n_samples,
            n_distinct_treatments=n_distinct_treatments,
            chosen_ite=chosen_ite,
            pct_outside_support=propensity_metrics["pct_outside_support"],
            pct_extreme=propensity_metrics["pct_extreme"],
            n_unmatched_treated=propensity_metrics["n_unmatched_treated"],
            n_matched_pairs=propensity_metrics["n_matched_pairs"],
        )
        alloc_rows.append([
            str(a.customer_id),
            f"{a.chosen_discount:,.2f}%",
            f"${a.budget_used:,.2f}",
            f"{confidence_result.confidence_score:.3f}",
            confidence_result.confidence_level,
        ])
    alloc_table = Table(alloc_rows, colWidths=[120, 100, 100, 90, 100], repeatRows=1)
    alloc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(alloc_table)

    doc.build(story)
    return buffer.getvalue()
