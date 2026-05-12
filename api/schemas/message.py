"""
Message Pydantic schemas (Pydantic v2).

Covers the client communication thread resource:
- MessageCreate       — POST /api/me/messages request body.
- MessageOut          — response shape for a single message.
- MessageListResponse — paginated list wrapper.

Body constraint (spec §messages): 1–4000 characters. Empty string and
oversized bodies are rejected at the Pydantic validation layer (HTTP 422).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MessageCreate(BaseModel):
    """Fields required to send a message in a client thread."""

    body: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Message body — must be between 1 and 4000 characters.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    """Single message representation returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    sender_user_id: uuid.UUID | None
    body: str
    attachments_json: list
    created_at: datetime


class MessageListResponse(BaseModel):
    """Paginated list of messages."""

    items: list[MessageOut]
    total: int
    limit: int
    offset: int
