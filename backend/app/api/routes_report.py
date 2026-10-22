"""GET /runs/{run_id}/report.csv and /report.pdf (Phase 3 -- downloadable reports)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.get("/runs/{run_id}/report.csv")
def get_csv_report(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    content = report_service.generate_csv(db, run_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id}_report.csv"},
    )


@router.get("/runs/{run_id}/report.pdf")
def get_pdf_report(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    content = report_service.generate_pdf(db, run_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id}_report.pdf"},
    )
