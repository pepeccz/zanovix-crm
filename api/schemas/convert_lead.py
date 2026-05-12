"""
Lead-to-client conversion request schema (Pydantic v2).

Per spec Q1 resolution: all fields are optional.
The service layer falls back to lead fields when body fields are absent.
Empty POST body MUST succeed if lead.company is set (name defaults to lead.company).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from api.schemas.billing_profile import BillingProfileCreate


class ConvertLeadBody(BaseModel):
    """
    Optional overrides for the client created from lead conversion.

    Absent fields default to corresponding lead fields:
      - name  → lead.company (or lead.name if company is None)
      - other → None (omitted from the client row)

    billing_profile: when present, creates a BillingProfile linked to the new
    client in the same atomic transaction (Option B, Design §5).
    """

    name: str | None = Field(default=None, max_length=200)
    sector: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=100)
    owner_id: uuid.UUID | None = None
    mrr_cents: int | None = Field(default=None, ge=0)
    stage: str | None = None
    billing_profile: BillingProfileCreate | None = None
