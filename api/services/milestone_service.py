"""
Milestone service — business logic for the Milestone aggregate.

Design principles:
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- services flush; routes commit.
- Activity log 'milestone_completed' is written only when completed_at flips null → not null.
- Domain exceptions are raised here and mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.milestone import MilestoneCreate, MilestoneUpdate
from api.services import activity_log_service
from api.services.exceptions import MilestoneNotFoundError, ServiceNotFoundError
from database.models.milestone import Milestone
from database.models.service import Service

logger = logging.getLogger(__name__)


class MilestoneService:
    """
    Service layer for the Milestone aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_service(self, service_id: uuid.UUID) -> Service:
        """Fetch service by id; raise ServiceNotFoundError if missing."""
        stmt = select(Service).where(Service.id == service_id)
        service = (await self.session.execute(stmt)).scalar_one_or_none()
        if service is None:
            raise ServiceNotFoundError(service_id)
        return service

    async def list_milestones(self, service_id: uuid.UUID) -> list[Milestone]:
        """
        Return all milestones for a service, ordered by their n index.

        # services flush; routes commit.
        """
        stmt = (
            select(Milestone)
            .where(Milestone.service_id == service_id)
            .order_by(Milestone.n)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def create_under_service(
        self,
        service_id: uuid.UUID,
        body: MilestoneCreate,
        actor_user_id: uuid.UUID,
    ) -> Milestone:
        """
        Persist a new Milestone under the given service.

        # services flush; routes commit.

        Raises:
            ServiceNotFoundError: if the parent service does not exist.
        """
        service = await self._get_service(service_id)

        milestone = Milestone(
            service_id=service_id,
            n=body.n,
            title=body.title,
            due_date=body.due_date,
        )
        self.session.add(milestone)
        await self.session.flush()
        await self.session.refresh(milestone)

        logger.info(
            "milestone_created",
            extra={
                "milestone_id": str(milestone.id),
                "service_id": str(service_id),
                "actor_user_id": str(actor_user_id),
            },
        )
        return milestone

    async def update(
        self,
        service_id: uuid.UUID,
        n: int,
        body: MilestoneUpdate,
        actor_user_id: uuid.UUID,
    ) -> Milestone:
        """
        Patch a milestone by (service_id, n).

        Writes 'milestone_completed' activity log only when completed_at
        flips from null → not null (first completion).

        # services flush; routes commit.

        Raises:
            MilestoneNotFoundError: if not found by (service_id, n).
        """
        stmt = select(Milestone).where(
            Milestone.service_id == service_id,
            Milestone.n == n,
        )
        milestone = (await self.session.execute(stmt)).scalar_one_or_none()
        if milestone is None:
            raise MilestoneNotFoundError(service_id, n)

        was_completed = milestone.completed_at is not None
        update_data = body.model_dump(exclude_unset=True)

        # If caller is setting completed_at for the first time, default to now()
        if "completed_at" in update_data and update_data["completed_at"] is None:
            pass  # explicit null-set — allow clearing
        elif "completed_at" not in update_data:
            pass  # not touching completed_at

        for field, value in update_data.items():
            setattr(milestone, field, value)

        await self.session.flush()

        # Write activity log only on the null → not null flip
        is_now_completed = milestone.completed_at is not None
        if not was_completed and is_now_completed:
            # Fetch parent service for client_id and title context
            service_stmt = select(Service).where(Service.id == service_id)
            service = (await self.session.execute(service_stmt)).scalar_one_or_none()
            if service is not None:
                await activity_log_service.append_activity(
                    self.session,
                    client_id=service.client_id,
                    kind="milestone_completed",
                    body=f"Milestone '{milestone.title}' completed (service='{service.title}')",
                    actor_user_id=actor_user_id,
                )

        await self.session.refresh(milestone)
        return milestone

    async def delete(
        self,
        service_id: uuid.UUID,
        n: int,
    ) -> None:
        """
        Delete a milestone by (service_id, n).

        # services flush; routes commit.

        Raises:
            MilestoneNotFoundError: if not found.
        """
        stmt = select(Milestone).where(
            Milestone.service_id == service_id,
            Milestone.n == n,
        )
        milestone = (await self.session.execute(stmt)).scalar_one_or_none()
        if milestone is None:
            raise MilestoneNotFoundError(service_id, n)

        await self.session.delete(milestone)
        await self.session.flush()
        logger.info(
            "milestone_deleted",
            extra={"service_id": str(service_id), "n": n},
        )
