"""
Milestone endpoints — nested under services.

Routes (all under prefix /api, registered in main.py):
  GET    /api/services/{service_id}/milestones    — list milestones
  POST   /api/services/{service_id}/milestones    — create milestone
  PATCH  /api/services/{service_id}/milestones/{n} — update milestone by ordering index
  DELETE /api/services/{service_id}/milestones/{n} — delete milestone (admin only)

Design principles (design §8):
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in MilestoneService.
  - services flush; routes commit.
  - Error mapping: domain exceptions → HTTP status codes via handlers in api/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from api.services.milestone_service import MilestoneService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["milestones"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/services/{service_id}/milestones  — all authenticated roles
# ---------------------------------------------------------------------------


@router.get(
    "/services/{service_id}/milestones",
    status_code=status.HTTP_200_OK,
    response_model=list[MilestoneRead],
    summary="List milestones for a service",
)
async def list_milestones(
    service_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> list[MilestoneRead]:
    """Return all milestones for the given service, ordered by n."""
    svc = MilestoneService(session)
    milestones = await svc.list_milestones(service_id)
    return [MilestoneRead.model_validate(m) for m in milestones]


# ---------------------------------------------------------------------------
# POST /api/services/{service_id}/milestones  — admin + comercial + consultor (own service)
# ---------------------------------------------------------------------------


@router.post(
    "/services/{service_id}/milestones",
    status_code=status.HTTP_201_CREATED,
    response_model=MilestoneRead,
    summary="Create a milestone under a service",
)
async def create_milestone(
    service_id: uuid.UUID,
    body: MilestoneCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> MilestoneRead:
    """Create a new milestone under the given service."""
    svc = MilestoneService(session)
    milestone = await svc.create_under_service(service_id, body, current_user.id)
    await session.commit()
    return MilestoneRead.model_validate(milestone)


# ---------------------------------------------------------------------------
# PATCH /api/services/{service_id}/milestones/{n}  — admin + comercial + consultor (own)
# ---------------------------------------------------------------------------


@router.patch(
    "/services/{service_id}/milestones/{n}",
    status_code=status.HTTP_200_OK,
    response_model=MilestoneRead,
    summary="Update a milestone by ordering index",
)
async def update_milestone(
    service_id: uuid.UUID,
    n: int,
    body: MilestoneUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> MilestoneRead:
    """
    Patch a milestone identified by (service_id, n).

    Writing completed_at for the first time (null → not null) emits
    a 'milestone_completed' activity log entry on the parent client.
    """
    svc = MilestoneService(session)
    milestone = await svc.update(service_id, n, body, current_user.id)
    await session.commit()
    return MilestoneRead.model_validate(milestone)


# ---------------------------------------------------------------------------
# DELETE /api/services/{service_id}/milestones/{n}  — admin only
# ---------------------------------------------------------------------------


@router.delete(
    "/services/{service_id}/milestones/{n}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a milestone by ordering index (admin only)",
)
async def delete_milestone(
    service_id: uuid.UUID,
    n: int,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Delete a milestone by (service_id, n). Admin only."""
    svc = MilestoneService(session)
    await svc.delete(service_id, n)
    await session.commit()
