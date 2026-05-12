"""
Ticket Pydantic schemas (Pydantic v2).

Covers the client support ticket resource:
- TicketCreate  — POST /api/me/tickets request body.
- TicketPatch   — PATCH /api/me/tickets/{id} request body (client-scoped, status excluded).
- TicketOut     — response shape for a single ticket (read operations).
- TicketListResponse — paginated list wrapper.

Priority values: high | medium | low  (DB CK: ck_ticket_priority)
Status values:   pending | in_progress | closed  (DB CK: ck_ticket_status)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Priority and status literals mirror the DB CheckConstraint values.
TicketPriority = Literal["high", "medium", "low"]
TicketStatus = Literal["pending", "in_progress", "closed"]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class TicketCreate(BaseModel):
    """Fields required to open a new support ticket."""

    title: str = Field(..., max_length=200, description="Short, descriptive ticket title.")
    priority: TicketPriority = Field(
        default="medium",
        description="Ticket priority: high, medium, or low.",
    )
    body: str | None = Field(
        default=None,
        description="Optional longer description of the issue.",
    )
    service_id: uuid.UUID | None = Field(
        default=None,
        description="Optional reference to a related service.",
    )


class TicketPatch(BaseModel):
    """
    Partial update for a client-scoped ticket (PATCH /api/me/tickets/{id}).

    Clients can update title, priority, and body only.
    Status changes are reserved for internal roles (admin/consultor/comercial)
    via PATCH /api/tickets/{id} in PR-3.
    """

    title: str | None = Field(default=None, max_length=200)
    priority: TicketPriority | None = None
    body: str | None = None


class TicketUpdate(BaseModel):
    """
    Partial update for an internal-facing ticket (PATCH /api/tickets/{id}).

    Internal roles (admin / consultor) can change all fields including status
    and assigned_to_user_id. Comercial can change title/priority/body/assigned_to
    but NOT status — that restriction is enforced in the route handler.
    """

    title: str | None = Field(default=None, max_length=200)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    body: str | None = None
    assigned_to_user_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TicketOut(BaseModel):
    """Full ticket representation returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    service_id: uuid.UUID | None
    title: str
    priority: str
    status: str
    body: str | None
    created_by_user_id: uuid.UUID | None
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""

    items: list[TicketOut]
    total: int
    limit: int
    offset: int
