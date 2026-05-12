"""
Activity log endpoints — admin-only, read-only.

Routes (all under prefix /api, registered in main.py):
  GET /api/activity — paginated list of activity log entries, newest first.
                      Optional ?client_id=<uuid> filter.

Design principles (design ADR-D2 + §9):
  - Admin-only: require_role("admin").
  - Default limit = 50, max = 200. Pre-Pydantic 400 guard matches clients route pattern.
  - Default ordering: created_at DESC.
  - Routes are thin: validate HTTP input, call service, serialize response.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.schemas.activity_log import ActivityLogListResponse, ActivityLogRead
from api.services.activity_log_service import list_activity
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["activity"])

_ACTIVITY_LIMIT_MAX = 200
_ACTIVITY_LIMIT_DEFAULT = 50


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/activity  — admin only
# ---------------------------------------------------------------------------


@router.get(
    "/activity",
    status_code=status.HTTP_200_OK,
    response_model=ActivityLogListResponse,
    summary="List recent activity entries across all clients (admin only)",
)
async def get_activity(
    request: Request,
    session: AsyncSession = Depends(_get_session),
    _user: User = Depends(require_role("admin")),
) -> ActivityLogListResponse:
    """
    Return a paginated list of ActivityLog entries ordered by created_at DESC.

    Query parameters:
    - limit   (int, default 50, max 200): number of entries per page.
    - offset  (int, default 0):           number of entries to skip.
    - client_id (UUID, optional):         filter to entries for a single client.

    limit > 200 → 400 (not 422) with {\"error\": \"limit_exceeds_max\", \"max\": 200}.
    """
    raw_limit = request.query_params.get("limit")
    if raw_limit is not None:
        try:
            if int(raw_limit) > _ACTIVITY_LIMIT_MAX:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "limit_exceeds_max", "max": _ACTIVITY_LIMIT_MAX},
                )
        except ValueError:
            pass  # let Pydantic/FastAPI handle non-integer values with 422

    limit = int(raw_limit) if raw_limit and raw_limit.isdigit() else _ACTIVITY_LIMIT_DEFAULT
    offset = int(request.query_params.get("offset", 0))

    raw_client_id = request.query_params.get("client_id")
    client_id: uuid.UUID | None = None
    if raw_client_id:
        try:
            client_id = uuid.UUID(raw_client_id)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={"error": "invalid_uuid", "field": "client_id"},
            )

    items, total = await list_activity(
        session,
        limit=limit,
        offset=offset,
        client_id=client_id,
    )

    return ActivityLogListResponse(
        items=[ActivityLogRead.model_validate(entry) for entry in items],
        total=total,
        limit=limit,
        offset=offset,
    )
