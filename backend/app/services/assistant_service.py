"""
AI assistant panel (Phase 3, Enhancement #10).

Generates a natural-language explanation of a run's recommendations from
its own computed KPI/refutation/drift data using templated NLG. This
intentionally does not call an external LLM API (no such credential is
configured for this backend); it is a deterministic, auditable summary
generator that a real LLM integration could later replace behind the same
endpoint.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import drift_repository, refutation_repository, run_repository
from app.schemas.assistant_schema import AssistantRequestSchema, AssistantResponseSchema
from app.services import summary_service


def ask(db: Session, run_id: int, payload: AssistantRequestSchema) -> AssistantResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"The assistant needs run {run_id} to finish before it can explain results.")

    summary = summary_service.get_summary(db, run_id)
    refutations = refutation_repository.list_by_run(db, run_id)
    drift_rows = drift_repository.list_by_run(db, run_id)

    question = (payload.question or "").lower().strip()

    if "drift" in question:
        drifted = [d.feature for d in drift_rows if d.drifted]
        if not drift_rows:
            answer = "No prior campaign was available to compare against, so drift status could not be computed for this run."
        elif drifted:
            answer = (
                f"Data drift was detected in {len(drifted)} feature(s) compared to the previous campaign: "
                f"{', '.join(drifted)}. Consider retraining before trusting these recommendations for a "
                f"significantly different customer population."
            )
        else:
            answer = "No significant data drift was detected relative to the previous campaign's customer data."
    elif "confiden" in question or "trust" in question or "refut" in question:
        passed = sum(1 for r in refutations if r.passed)
        total = len(refutations) or 1
        answer = (
            f"{passed} of {total} causal refutation tests passed for this run, which is the evidence that the "
            f"estimated treatment effects are not simply an artifact of confounding or noise. "
            + ("This gives reasonably strong confidence in the recommendations." if passed == total else
               "Some tests did not pass, so recommendations should be reviewed before large-scale rollout.")
        )
    elif "budget" in question or "spend" in question:
        answer = (
            f"This campaign used ${summary.budget_used:,.2f} of its ${summary.budget:,.2f} budget "
            f"({summary.budget_utilization_pct:.1f}% utilization), targeting {summary.customers_targeted} of "
            f"{summary.customers_total} customers with an average discount of {summary.average_discount:,.2f}%."
        )
    elif "roi" in question or "revenue" in question:
        answer = (
            f"The optimized allocation is estimated to generate ${summary.incremental_revenue:,.2f} in incremental "
            f"revenue, a {summary.roi_improvement_pct:+.1f} percentage-point ROI improvement over giving every "
            f"customer the same average discount, saving an estimated ${summary.savings_vs_blanket:,.2f}."
        )
    else:
        answer = (
            f"Campaign '{summary.campaign_name}' (run #{summary.run_id}) targeted {summary.customers_targeted} of "
            f"{summary.customers_total} customers, spending ${summary.budget_used:,.2f} of a ${summary.budget:,.2f} "
            f"budget ({summary.budget_utilization_pct:.1f}% utilization) at an average discount of "
            f"{summary.average_discount:,.2f}%. The causally-optimized allocation is estimated to produce "
            f"${summary.incremental_revenue:,.2f} in incremental revenue, a {summary.roi_improvement_pct:+.1f} "
            f"percentage-point ROI improvement over blanket targeting. Ask me about budget, ROI, drift, or "
            f"confidence for more detail."
        )

    return AssistantResponseSchema(run_id=run_id, answer=answer)
