"""
Contact Pydantic schemas (Pydantic v2).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ContactCreate(BaseModel):
    """Fields required to create a contact under a client."""

    client_id: uuid.UUID
    name: str = Field(..., max_length=200)
    role: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_primary: bool = False


class ContactUpdate(BaseModel):
    """Partial update for a contact. All fields optional."""

    name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_primary: bool | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ContactRead(BaseModel):
    """Full contact representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    client_id: uuid.UUID
    name: str
    role: str | None
    email: str | None
    phone: str | None
    is_primary: bool
