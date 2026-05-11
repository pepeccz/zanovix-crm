"""
Milestone Pydantic schemas (Pydantic v2).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MilestoneCreate(BaseModel):
    """Fields required to create a new milestone under a service."""

    n: int = Field(..., ge=1, description="Ordering index scoped per service.")
    title: str = Field(..., max_length=300)
    due_date: date | None = None


class MilestoneUpdate(BaseModel):
    """Partial update for a milestone. All fields optional."""

    title: str | None = Field(default=None, max_length=300)
    due_date: date | None = None
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MilestoneRead(BaseModel):
    """Full milestone representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    n: int
    title: str
    due_date: date | None
    completed_at: datetime | None
