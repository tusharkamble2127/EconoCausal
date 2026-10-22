"""AI assistant natural-language explanation endpoint (Phase 3)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AssistantRequestSchema(BaseModel):
    question: Optional[str] = None


class AssistantResponseSchema(BaseModel):
    run_id: int
    answer: str
