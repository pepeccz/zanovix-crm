"""
Client service — business logic for the Client aggregate.

Design principles:
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- RBAC scoping is handled HERE, not in route handlers.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- services flush; routes commit.
- Domain exceptions are raised here and mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.domain.client_stage_machine import ClientStageMachine
from api.domain.status_machine import InvalidTransitionError as DomainInvalidTransitionError
from api.schemas.client import ClientCreate, ClientFilters, ClientUpdate
from api.schemas.convert_lead import ConvertLeadBody
from api.services import activity_log_service
from api.services.exceptions import (
    ClientNotFoundError,
    InvalidTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    LeadNotQualifiedError,
)
from database.models.activity_log import ActivityLog
from database.models.client import Client
from database.models.contact import Contact
from database.models.lead import Lead
from database.models.service import Service
from database.models.user import User

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


class ClientService:
    """
    Service layer for the Client aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Read ───────────────────────────────────────────────────────────────

    async def list_clients(
        self,
        user: User,
        filters: ClientFilters,
    ) -> tuple[list[Client], int]:
        """
        Return a paginated, scoped list of clients.

        # services flush; routes commit.

        RBAC:
        - admin    → all clients
        - consultor/comercial → only clients where owner_id == user.id
        """
        stmt = select(Client).order_by(Client.created_at.desc())
        count_stmt = select(func.count(Client.id))

        # RBAC scoping
        if user.role in ("consultor", "comercial"):
            stmt = stmt.where(Client.owner_id == user.id)
            count_stmt = count_stmt.where(Client.owner_id == user.id)

        # Optional filters
        if filters.stage is not None:
            stmt = stmt.where(Client.stage == filters.stage)
            count_stmt = count_stmt.where(Client.stage == filters.stage)
        if filters.owner_id is not None:
            stmt = stmt.where(Client.owner_id == filters.owner_id)
            count_stmt = count_stmt.where(Client.owner_id == filters.owner_id)
        if filters.sector is not None:
            stmt = stmt.where(Client.sector == filters.sector)
            count_stmt = count_stmt.where(Client.sector == filters.sector)
        if filters.q is not None:
            pattern = f"%{filters.q}%"
            stmt = stmt.where(Client.name.ilike(pattern))
            count_stmt = count_stmt.where(Client.name.ilike(pattern))

        stmt = stmt.limit(filters.limit).offset(filters.offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def get_client_detail(
        self,
        user: User,
        client_id: uuid.UUID,
    ) -> tuple[Client, list[ActivityLog]]:
        """
        Fetch a single client with eager-loaded contacts, services (with milestones),
        owner, plus the last 20 activity log rows (separate query).

        # services flush; routes commit.

        Raises:
            ClientNotFoundError: if not found or outside user's ownership scope.
        """
        stmt = (
            select(Client)
            .where(Client.id == client_id)
            .options(
                selectinload(Client.contacts),
                selectinload(Client.services).selectinload(Service.milestones),
                selectinload(Client.owner),
            )
        )
        if user.role in ("consultor", "comercial"):
            stmt = stmt.where(Client.owner_id == user.id)

        client = (await self.session.execute(stmt)).scalar_one_or_none()
        if client is None:
            raise ClientNotFoundError(client_id)

        activity_stmt = (
            select(ActivityLog)
            .where(ActivityLog.client_id == client_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(20)
        )
        recent_activity = (await self.session.execute(activity_stmt)).scalars().all()
        return client, list(recent_activity)

    async def get_for_user(self, user: User, client_id: uuid.UUID) -> Client:
        """
        Fetch a single client, applying RBAC scoping. No eager loading.

        Raises ClientNotFoundError if not found or outside scope.
        """
        stmt = select(Client).where(Client.id == client_id)
        if user.role in ("consultor", "comercial"):
            stmt = stmt.where(Client.owner_id == user.id)

        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if result is None:
            raise ClientNotFoundError(client_id)
        return result

    # ─── Write ──────────────────────────────────────────────────────────────

    async def create_client(
        self,
        body: ClientCreate,
        actor_user_id: uuid.UUID,
    ) -> Client:
        """
        Persist a new Client and write an initial 'stage_change' activity log entry.

        # services flush; routes commit.
        """
        client = Client(
            name=body.name,
            sector=body.sector,
            size=body.size,
            region=body.region,
            owner_id=body.owner_id,
            mrr_cents=body.mrr_cents,
            stage=body.stage if body.stage is not None else "lead",
        )
        self.session.add(client)
        await self.session.flush()

        initial_stage = client.stage
        await activity_log_service.append_activity(
            self.session,
            client_id=client.id,
            kind="stage_change",
            body=f"Client created at stage: {initial_stage}",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(client)
        logger.info(
            "client_created",
            extra={"client_id": str(client.id), "actor_user_id": str(actor_user_id)},
        )
        return client

    async def update_client(
        self,
        user: User,
        client_id: uuid.UUID,
        body: ClientUpdate,
    ) -> Client:
        """
        Patch non-stage fields on a client.

        # services flush; routes commit.

        Stage changes must use change_stage() — this method ignores the stage field
        (ClientUpdate schema excludes it per REQ-10).
        """
        client = await self.get_for_user(user, client_id)

        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(client, field, value)

        await self.session.flush()
        await self.session.refresh(client)
        return client

    async def change_stage(
        self,
        user: User,
        client_id: uuid.UUID,
        new_stage: str,
        force: bool = False,
    ) -> Client:
        """
        Transition a client's stage, enforcing ClientStageMachine rules.

        # services flush; routes commit.

        Raises:
            ClientNotFoundError:    client not found or outside user's scope.
            InvalidTransitionError: transition not permitted by state machine.
        """
        client = await self.get_for_user(user, client_id)

        try:
            ClientStageMachine.assert_can_transition(client.stage, new_stage, force=force)
        except DomainInvalidTransitionError as exc:
            allowed = ClientStageMachine.valid_transitions.get(client.stage, set())
            logger.warning(
                "invalid_stage_transition_attempted",
                extra={
                    "client_id": str(client_id),
                    "from": client.stage,
                    "to": new_stage,
                    "actor_user_id": str(user.id),
                },
            )
            raise InvalidTransitionError(exc.from_status, exc.to_status, allowed) from exc

        old_stage = client.stage
        client.stage = new_stage
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client.id,
            kind="stage_change",
            body=f"Stage: {old_stage} → {new_stage}",
            actor_user_id=user.id,
        )

        await self.session.refresh(client)
        logger.info(
            "client_stage_changed",
            extra={
                "client_id": str(client_id),
                "from_stage": old_stage,
                "to_stage": new_stage,
                "actor_user_id": str(user.id),
            },
        )
        return client

    async def convert_from_lead(
        self,
        lead_id: uuid.UUID,
        body: ConvertLeadBody,
        actor_user_id: uuid.UUID,
    ) -> Client:
        """
        Atomically convert a qualified lead into a client.

        # services flush; routes commit.

        This method is atomic within the route's transaction — it uses
        session.flush() only; the route's session.commit() covers the whole
        transaction. If any step raises an exception, the route's exception
        handler (or FastAPI's default) will rollback the session.

        Raises:
            LeadNotFoundError:         lead not found.
            LeadNotQualifiedError:     lead.status != 'qualified'.
            LeadAlreadyConvertedError: lead.converted_client_id is already set.
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        lead = (await self.session.execute(stmt)).scalar_one_or_none()
        if lead is None:
            raise LeadNotFoundError(lead_id)

        if lead.status != "qualified":
            raise LeadNotQualifiedError(lead_id, lead.status)

        if lead.converted_client_id is not None:
            raise LeadAlreadyConvertedError(lead_id, lead.converted_client_id)

        # Resolve client fields — body fields take precedence; fall back to lead data
        client_name = body.name or lead.company or lead.name
        client = Client(
            name=client_name,
            sector=body.sector,
            size=body.size,
            region=body.region,
            owner_id=body.owner_id,
            mrr_cents=body.mrr_cents,
            stage=body.stage if body.stage is not None else "lead",
        )
        self.session.add(client)
        await self.session.flush()

        # Update lead linkage
        lead.status = "converted"
        lead.converted_client_id = client.id
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client.id,
            kind="lead_converted",
            body=f"Lead {lead.name} converted to client",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(client)
        logger.info(
            "lead_converted_to_client",
            extra={
                "lead_id": str(lead_id),
                "client_id": str(client.id),
                "actor_user_id": str(actor_user_id),
            },
        )
        return client
