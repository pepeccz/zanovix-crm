"""
Client Pydantic schemas (Pydantic v2).

Two response shapes:
- ClientRead      — flat, used in list endpoints and write-op responses.
- ClientDetailResponse — nested, used exclusively by GET /api/clients/{id}.

Per Design §10 (ADR-11): milestones are NOT included in the client detail response;
they are fetched on demand via GET /api/services/{id}.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.activity_log import ActivityLogRead
from api.schemas.billing_profile import BillingProfileRead
from api.schemas.contact import ContactRead
from api.schemas.service import ServiceStub


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ClientCreate(BaseModel):
    """Fields to create a new client."""

    name: str = Field(..., max_length=200)
    sector: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=100)
    owner_id: uuid.UUID | None = None
    mrr_cents: int | None = Field(default=None, ge=0)
    stage: str = Field(default="lead")


class ClientUpdate(BaseModel):
    """Partial update for client metadata. Stage is excluded — use the stage endpoint."""

    name: str | None = Field(default=None, max_length=200)
    sector: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=100)
    owner_id: uuid.UUID | None = None
    mrr_cents: int | None = Field(default=None, ge=0)
    lifetime_value_cents: int | None = Field(default=None, ge=0)


class ClientStageChange(BaseModel):
    """Payload for PATCH /api/clients/{id}/stage."""

    stage: str = Field(..., description="Target stage for the client stage machine.")


class ClientFilters(BaseModel):
    """Query parameters for GET /api/clients."""

    stage: str | None = None
    owner_id: uuid.UUID | None = None
    sector: str | None = None
    q: str | None = Field(default=None, description="ILIKE search on client name.")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ClientRead(BaseModel):
    """Flat client representation — used in list endpoints and mutation responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    sector: str | None
    size: str | None
    region: str | None
    owner_id: uuid.UUID | None
    stage: str
    entered_at: datetime
    mrr_cents: int | None
    lifetime_value_cents: int | None


class ClientDetailResponse(BaseModel):
    """
    Full client detail — only returned by GET /api/clients/{id}.

    Nests contacts, service stubs (without milestones), and last 20 activity entries.
    Milestones are fetched on demand via GET /api/services/{id}.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    sector: str | None
    size: str | None
    region: str | None
    owner_id: uuid.UUID | None
    stage: str
    entered_at: datetime
    mrr_cents: int | None
    lifetime_value_cents: int | None
    contacts: list[ContactRead]
    services: list[ServiceStub]
    billing_profiles: list[BillingProfileRead]
    recent_activity: list[ActivityLogRead]


class ClientListResponse(BaseModel):
    """Paginated list of clients (flat ClientRead items)."""

    items: list[ClientRead]
    total: int
    limit: int
    offset: int
