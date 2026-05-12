"""
Lead Pydantic schemas (Pydantic v2).

Note on raw_payload: the field EXISTS on the Lead ORM model and is stored in the DB
for admin debugging purposes. It is intentionally EXCLUDED from LeadRead to prevent
leaking sanitized request metadata (headers, hashed IP) to API consumers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Valid value sets (mirrors DB CHECK constraints)
# ---------------------------------------------------------------------------

LeadVertical = Literal["clinicas_dentales", "general"]

LeadChannel = Literal[
    "email_marketing",
    "cold_calling",
    "networking",
    "referral",
    "web_form",
    "other",
]

LeadStatus = Literal[
    "new",
    "contacted",
    "qualified",
    "disqualified",
    "converted",
]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class LeadCreate(BaseModel):
    """Public intake form fields. All server-set fields (id, status, etc.) are excluded."""

    name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)
    vertical: LeadVertical
    channel: LeadChannel
    source_url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=2000)
    role: str | None = Field(default=None, max_length=100)


class LeadUpdate(BaseModel):
    """Partial update for lead editable fields."""

    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    role: str | None = Field(default=None, max_length=100)


class LeadStatusUpdate(BaseModel):
    """Payload for PATCH /api/leads/{id}/status."""

    status: LeadStatus


class LeadAssign(BaseModel):
    """Payload for PATCH /api/leads/{id}/assign (admin only)."""

    owner_id: uuid.UUID


class LeadFilters(BaseModel):
    """Query parameters for GET /api/leads."""

    vertical: LeadVertical | None = None
    channel: LeadChannel | None = None
    status: LeadStatus | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class LeadRead(BaseModel):
    """
    Full lead representation returned to API consumers.

    raw_payload is intentionally excluded — it contains sanitized request metadata
    (filtered headers, hashed IP) intended for internal debugging only.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    email: str
    phone: str | None
    company: str | None
    vertical: str
    channel: str
    source_url: str | None
    notes: str | None
    status: str
    owner_id: uuid.UUID | None
    role: str | None


class LeadListResponse(BaseModel):
    """Paginated list of leads."""

    items: list[LeadRead]
    total: int
    limit: int
    offset: int
