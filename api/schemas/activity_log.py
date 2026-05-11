"""
ActivityLog Pydantic schemas (Pydantic v2).

ActivityLog entries are immutable — no Create/Update schemas are exposed publicly.
Writes happen exclusively through the internal activity_log_service.write() helper.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ActivityLogRead(BaseModel):
    """Single activity log entry returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    client_id: uuid.UUID
    kind: str
    actor_user_id: uuid.UUID | None
    body: str


class ActivityLogListResponse(BaseModel):
    """Paginated list of activity log entries."""

    items: list[ActivityLogRead]
    total: int
    limit: int
    offset: int
