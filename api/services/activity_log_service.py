"""
ActivityLog service — internal helper for appending audit/activity rows.

Design principles:
- This module is NOT exposed via any HTTP route. It is a shared helper called
  exclusively by other service modules within the same async session.
- services flush; routes commit.
- activity_log_service.write() is the SINGLE ingress point for ActivityLog rows (ADR-3).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.activity_kinds import ACTIVITY_KINDS
from database.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


async def append_activity(
    session: AsyncSession,
    client_id: uuid.UUID,
    kind: str,
    body: str,
    actor_user_id: uuid.UUID | None = None,
) -> ActivityLog:
    """
    Append one ActivityLog row inside an existing session/transaction.

    # services flush; routes commit.

    This helper does session.add() + session.flush() but NEVER session.commit().
    The surrounding transaction (owned by the route) is responsible for the final commit.

    Args:
        session:       The active AsyncSession for this request.
        client_id:     FK to the Client this event belongs to.
        kind:          Activity kind string — must be in ACTIVITY_KINDS whitelist.
        body:          Human-readable description of the event.
        actor_user_id: UUID of the user who triggered the event, or None for system.

    Returns:
        The flushed (but not committed) ActivityLog ORM instance.

    Raises:
        ValueError: if `kind` is not in the ACTIVITY_KINDS whitelist (fail-fast
                    before a DB CheckConstraint violation surfaces a cryptic error).
    """
    if kind not in ACTIVITY_KINDS:
        raise ValueError(
            f"Invalid activity kind '{kind}'. "
            f"Allowed: {sorted(ACTIVITY_KINDS)}"
        )

    entry = ActivityLog(
        client_id=client_id,
        kind=kind,
        body=body,
        actor_user_id=actor_user_id,
    )
    session.add(entry)
    await session.flush()

    logger.debug(
        "activity_log_appended",
        extra={
            "client_id": str(client_id),
            "kind": kind,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
        },
    )
    return entry
