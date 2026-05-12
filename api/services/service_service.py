"""
Service service — business logic for the Service aggregate.

Design principles:
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- RBAC scoping for consultor (own service only) is handled HERE.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- services flush; routes commit.
- Domain exceptions are raised here and mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.domain.service_state_machine import ServiceStateMachine
from api.domain.status_machine import InvalidTransitionError as DomainInvalidTransitionError
from api.schemas.service import ServiceCreate, ServiceFilters, ServiceUpdate
from api.services import activity_log_service
from api.services.exceptions import (
    CannotCreateOnLostClientError,
    ClientNotFoundError,
    InvalidTransitionError,
    ServiceNotFoundError,
)
from database.models.client import Client
from database.models.milestone import Milestone
from database.models.service import Service
from database.models.user import User

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


class ServiceService:
    """
    Service layer for the Service aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Read ───────────────────────────────────────────────────────────────

    async def list_for_client(
        self,
        *,
        client_id_filter: uuid.UUID | None,
        limit: int = 50,
        offset: int = 0,
        state: str | None = None,
        type: str | None = None,
    ) -> tuple[list[Service], int]:
        """
        Return a paginated list of services scoped to a client_id.

        Used exclusively by /api/me/* endpoints (client_user branch).
        When client_id_filter is not None, only services for that client are returned.
        When None (internal branch calling this method), all services are returned.

        # services flush; routes commit (read-only here).
        """
        stmt = select(Service).order_by(Service.created_at.desc())
        count_stmt = select(func.count(Service.id))

        if client_id_filter is not None:
            stmt = stmt.where(Service.client_id == client_id_filter)
            count_stmt = count_stmt.where(Service.client_id == client_id_filter)

        if state is not None:
            stmt = stmt.where(Service.state == state)
            count_stmt = count_stmt.where(Service.state == state)

        if type is not None:
            stmt = stmt.where(Service.type == type)
            count_stmt = count_stmt.where(Service.type == type)

        stmt = stmt.limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def get_for_client(
        self,
        service_id: uuid.UUID,
        *,
        client_id_filter: uuid.UUID | None,
    ) -> Service:
        """
        Fetch a single service, applying client_id_filter when provided.

        Out-of-scope or missing services raise ServiceNotFoundError (→ HTTP 404).
        Eager-loads milestones for the service-detail endpoint.

        Raises:
            ServiceNotFoundError: service not found or outside caller's client scope.
        """
        stmt = (
            select(Service)
            .where(Service.id == service_id)
            .options(selectinload(Service.milestones))
        )
        if client_id_filter is not None:
            stmt = stmt.where(Service.client_id == client_id_filter)

        service = (await self.session.execute(stmt)).scalar_one_or_none()
        if service is None:
            raise ServiceNotFoundError(service_id)
        return service

    async def list_services(
        self,
        user: User,
        filters: ServiceFilters,
    ) -> tuple[list[Service], int]:
        """
        Return a paginated list of services.

        # services flush; routes commit.

        RBAC:
        - admin/comercial → all services (optionally filtered by client_id/owner_id)
        - consultor       → only services where owner_id == user.id
        """
        stmt = select(Service).order_by(Service.created_at.desc())
        count_stmt = select(func.count(Service.id))

        # RBAC scoping for consultor
        if user.role == "consultor":
            stmt = stmt.where(Service.owner_id == user.id)
            count_stmt = count_stmt.where(Service.owner_id == user.id)

        # Optional filters
        if filters.client_id is not None:
            stmt = stmt.where(Service.client_id == filters.client_id)
            count_stmt = count_stmt.where(Service.client_id == filters.client_id)
        if filters.owner_id is not None:
            stmt = stmt.where(Service.owner_id == filters.owner_id)
            count_stmt = count_stmt.where(Service.owner_id == filters.owner_id)
        if filters.state is not None:
            stmt = stmt.where(Service.state == filters.state)
            count_stmt = count_stmt.where(Service.state == filters.state)
        if filters.type is not None:
            stmt = stmt.where(Service.type == filters.type)
            count_stmt = count_stmt.where(Service.type == filters.type)

        stmt = stmt.limit(filters.limit).offset(filters.offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def get_service_detail(
        self,
        user: User,
        service_id: uuid.UUID,
    ) -> Service:
        """
        Fetch a single service with selectinload(milestones).

        # services flush; routes commit.

        Raises:
            ServiceNotFoundError: if not found or consultor accessing another owner's service.
        """
        stmt = (
            select(Service)
            .where(Service.id == service_id)
            .options(selectinload(Service.milestones))
        )
        if user.role == "consultor":
            stmt = stmt.where(Service.owner_id == user.id)

        service = (await self.session.execute(stmt)).scalar_one_or_none()
        if service is None:
            raise ServiceNotFoundError(service_id)
        return service

    async def _get_service_for_write(
        self,
        user: User,
        service_id: uuid.UUID,
    ) -> Service:
        """
        Fetch a service for mutation, applying consultor RBAC scoping.

        Consultor can only mutate their own services (owner_id == user.id).
        Returns 404-equivalent (ServiceNotFoundError) for out-of-scope — prevents
        existence leaking (spec REQ-14-C).
        """
        stmt = select(Service).where(Service.id == service_id)
        if user.role == "consultor":
            stmt = stmt.where(Service.owner_id == user.id)

        service = (await self.session.execute(stmt)).scalar_one_or_none()
        if service is None:
            raise ServiceNotFoundError(service_id)
        return service

    # ─── Write ──────────────────────────────────────────────────────────────

    async def create_service(
        self,
        body: ServiceCreate,
        actor_user_id: uuid.UUID,
    ) -> Service:
        """
        Persist a new Service. Rejects creation on a 'lost' client (REQ-16).

        # services flush; routes commit.

        Raises:
            ClientNotFoundError:         if the parent client does not exist.
            CannotCreateOnLostClientError: if client.stage == 'lost'.
        """
        # Validate parent client exists and is not lost
        client_stmt = select(Client).where(Client.id == body.client_id)
        client = (await self.session.execute(client_stmt)).scalar_one_or_none()
        if client is None:
            raise ClientNotFoundError(body.client_id)

        if client.stage == "lost":
            raise CannotCreateOnLostClientError(body.client_id)

        service = Service(
            client_id=body.client_id,
            owner_id=body.owner_id,
            type=body.type,
            title=body.title,
            state="scoping",
            setup_price_cents=body.setup_price_cents,
            monthly_cents=body.monthly_cents,
        )
        self.session.add(service)
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=body.client_id,
            kind="service_started",
            body=f"Service '{service.title}' started (type={service.type})",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(service)
        logger.info(
            "service_created",
            extra={
                "service_id": str(service.id),
                "client_id": str(body.client_id),
                "actor_user_id": str(actor_user_id),
            },
        )
        return service

    async def update_service(
        self,
        user: User,
        service_id: uuid.UUID,
        body: ServiceUpdate,
    ) -> Service:
        """
        Patch general (non-state) fields on a service.

        # services flush; routes commit.

        Raises:
            ServiceNotFoundError: if not found or out of scope for consultor.
        """
        service = await self._get_service_for_write(user, service_id)

        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)

        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def change_state(
        self,
        user: User,
        service_id: uuid.UUID,
        new_state: str,
    ) -> Service:
        """
        Transition a service's state, enforcing ServiceStateMachine rules.

        # services flush; routes commit.

        Raises:
            ServiceNotFoundError:   service not found or out of scope for consultor.
            InvalidTransitionError: transition not permitted by state machine.
        """
        service = await self._get_service_for_write(user, service_id)

        try:
            ServiceStateMachine.assert_can_transition(service.state, new_state)
        except DomainInvalidTransitionError as exc:
            allowed = ServiceStateMachine.valid_transitions.get(service.state, set())
            logger.warning(
                "invalid_service_state_transition_attempted",
                extra={
                    "service_id": str(service_id),
                    "from": service.state,
                    "to": new_state,
                    "actor_user_id": str(user.id),
                },
            )
            raise InvalidTransitionError(exc.from_status, exc.to_status, allowed) from exc

        old_state = service.state
        service.state = new_state
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=service.client_id,
            kind="service_state_change",
            body=f"Service '{service.title}' state: {old_state} → {new_state}",
            actor_user_id=user.id,
        )

        await self.session.refresh(service)
        logger.info(
            "service_state_changed",
            extra={
                "service_id": str(service_id),
                "from_state": old_state,
                "to_state": new_state,
                "actor_user_id": str(user.id),
            },
        )
        return service
