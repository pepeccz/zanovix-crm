"""
Service Pydantic schemas (Pydantic v2).

ServiceRead nests MilestoneRead for the service-detail endpoint.
ServiceStub is a lightweight projection used inside ClientDetailResponse.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.milestone import MilestoneRead


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ServiceCreate(BaseModel):
    """Fields required to create a new service under a client."""

    client_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    type: str = Field(..., description="One of: assessment, development, formation")
    title: str = Field(..., max_length=200)
    setup_price_cents: int | None = Field(default=None, ge=0)
    monthly_cents: int | None = Field(default=None, ge=0)


class ServiceUpdate(BaseModel):
    """Partial update for service metadata. All fields optional."""

    title: str | None = Field(default=None, max_length=200)
    owner_id: uuid.UUID | None = None
    progress_pct: int | None = Field(default=None, ge=0, le=100)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    setup_price_cents: int | None = Field(default=None, ge=0)
    monthly_cents: int | None = Field(default=None, ge=0)
    score_int: int | None = Field(default=None, ge=0, le=100)


class ServiceStateChange(BaseModel):
    """Payload for PATCH /api/services/{id}/state."""

    state: str = Field(..., description="Target state for the service state machine.")


class ServiceFilters(BaseModel):
    """Query parameters for listing services."""

    state: str | None = None
    client_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    type: str | None = Field(default=None, description="One of: assessment, development, formation")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ServiceStub(BaseModel):
    """Lightweight service projection — used inside ClientDetailResponse."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    type: str
    state: str
    progress_pct: int | None
    owner_id: uuid.UUID | None


class ServiceRead(BaseModel):
    """Full service representation with nested milestones."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    client_id: uuid.UUID
    owner_id: uuid.UUID | None
    type: str
    title: str
    state: str
    progress_pct: int | None
    started_at: datetime | None
    ended_at: datetime | None
    setup_price_cents: int | None
    monthly_cents: int | None
    score_int: int | None
    milestones: list[MilestoneRead]


class ServiceListResponse(BaseModel):
    """Paginated list of services."""

    items: list[ServiceRead]
    total: int
    limit: int
    offset: int
