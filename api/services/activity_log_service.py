"""
ActivityLog service — internal helper for appending audit/activity rows,
and listing activity entries for the admin activity feed.

Design principles:
- append_activity() is the SINGLE ingress point for ActivityLog rows (ADR-3).
  It is called exclusively by other service modules within the same async session.
- list_activity() is called by the activity route handler (GET /api/activity).
- services flush; routes commit.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
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


async def list_activity(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    client_id: uuid.UUID | None = None,
) -> tuple[list[ActivityLog], int]:
    """
    Return a paginated list of ActivityLog rows, ordered by created_at DESC.

    Optionally filtered to a single client when `client_id` is provided.

    Args:
        session:   Active AsyncSession (read-only query, no flush/commit).
        limit:     Maximum number of entries to return (max 200, default 50).
        offset:    Number of entries to skip (for pagination).
        client_id: Optional UUID — when set, only entries for this client are returned.

    Returns:
        Tuple of (items, total) where `total` is the unfiltered row count
        matching the same predicate (used for pagination metadata).
    """
    base_filter = []
    if client_id is not None:
        base_filter.append(ActivityLog.client_id == client_id)

    count_stmt = select(func.count(ActivityLog.id))
    if base_filter:
        count_stmt = count_stmt.where(*base_filter)
    total: int = (await session.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if base_filter:
        list_stmt = list_stmt.where(*base_filter)

    items: list[ActivityLog] = list(
        (await session.execute(list_stmt)).scalars().all()
    )

    logger.debug(
        "list_activity_queried",
        extra={"limit": limit, "offset": offset, "total": total},
    )
    return items, total
