"""
Diagnostic Pydantic schemas (Pydantic v2).

Covers the assessment diagnostic JSON structure stored in services.diagnostic_json.
These are READ-ONLY schemas — admin edits the raw JSONB column directly in this slice.

Structure (design §D6):
  {
    "dimensions": {
      "data": 0-100,
      "processes": 0-100,
      "team": 0-100,
      "infrastructure": 0-100,
      "compliance": 0-100,
      "leadership": 0-100
    },
    "plan": [
      {"title": "...", "status": "go|wait|skip", "body": "..."},
      ...
    ],
    "summary": "Executive summary text"
  }
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested schemas
# ---------------------------------------------------------------------------


class DiagnosticDimensions(BaseModel):
    """Six maturity dimensions, each scored 0–100."""

    data: int = Field(..., ge=0, le=100)
    processes: int = Field(..., ge=0, le=100)
    team: int = Field(..., ge=0, le=100)
    infrastructure: int = Field(..., ge=0, le=100)
    compliance: int = Field(..., ge=0, le=100)
    leadership: int = Field(..., ge=0, le=100)


class DiagnosticPlanItem(BaseModel):
    """A single item in the diagnostic action plan."""

    title: str
    status: Literal["go", "wait", "skip"]
    body: str


# ---------------------------------------------------------------------------
# Top-level read schema
# ---------------------------------------------------------------------------


class DiagnosticRead(BaseModel):
    """
    Full diagnostic read representation.

    Parsed from services.diagnostic_json for GET /api/me/services/{id}/diagnostic.
    Returns None from the service layer when the service has no diagnostic data.
    """

    dimensions: DiagnosticDimensions
    plan: list[DiagnosticPlanItem] = Field(default_factory=list)
    summary: str
