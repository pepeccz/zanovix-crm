"""
Lead service — business logic for the Lead aggregate.

Design principles (design §4.2):
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- RBAC scoping is handled HERE, not in route handlers.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- Domain exceptions (LeadNotFoundError, InvalidTransitionError) are raised here and
  mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.status_machine import (
    InvalidTransitionError as DomainInvalidTransitionError,
    LeadStatusMachine,
)
from api.schemas.lead import LeadCreate, LeadFilters, LeadUpdate
from api.services.exceptions import (
    InvalidTransitionError,
    LeadNotFoundError,
)
from database.models.lead import Lead
from database.models.user import User

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Decision #2: limit > 200 is REJECTED with 400, not silently clamped.
# This is enforced at the schema layer (LeadFilters.limit le=200) and documented here.
MAX_LIMIT = 200


class LeadService:
    """
    Service layer for the Lead aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: LeadCreate, raw_payload: dict) -> Lead:
        """
        Persist a new Lead from a public intake submission.

        Args:
            payload:     Validated LeadCreate schema.
            raw_payload: Pre-sanitized request snapshot (from build_raw_payload).

        Returns:
            The newly created Lead ORM instance (flushed, not yet committed).
        """
        lead = Lead(
            name=payload.name,
            email=str(payload.email),
            phone=payload.phone,
            company=payload.company,
            vertical=payload.vertical,
            channel=payload.channel,
            source_url=str(payload.source_url) if payload.source_url else None,
            notes=payload.notes,
            role=payload.role,
            raw_payload=raw_payload,
        )
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)

        logger.info(
            "lead_created",
            extra={
                "lead_id": str(lead.id),
                "vertical": lead.vertical,
                "channel": lead.channel,
                "ip_hashed": raw_payload.get("client_ip_hashed"),
                "user_agent": raw_payload.get("headers", {}).get("user-agent"),
            },
        )
        return lead

    async def list_for_user(
        self,
        user: User,
        filters: LeadFilters,
    ) -> tuple[list[Lead], int]:
        """
        Return a paginated list of leads scoped to the requesting user's role.

        RBAC:
        - admin    → all leads
        - consultor/comercial → only leads where owner_id == user.id

        Args:
            user:    The authenticated requesting user.
            filters: Validated LeadFilters (vertical, channel, status, limit, offset).

        Returns:
            Tuple of (leads_page, total_count_pre_pagination).
        """
        stmt = select(Lead).order_by(Lead.created_at.desc())
        count_stmt = select(func.count(Lead.id))

        # RBAC scoping
        if user.role in ("consultor", "comercial"):
            stmt = stmt.where(Lead.owner_id == user.id)
            count_stmt = count_stmt.where(Lead.owner_id == user.id)
        # admin: no scoping filter

        # Optional filters (AND-combined)
        if filters.vertical is not None:
            stmt = stmt.where(Lead.vertical == filters.vertical)
            count_stmt = count_stmt.where(Lead.vertical == filters.vertical)
        if filters.channel is not None:
            stmt = stmt.where(Lead.channel == filters.channel)
            count_stmt = count_stmt.where(Lead.channel == filters.channel)
        if filters.status is not None:
            stmt = stmt.where(Lead.status == filters.status)
            count_stmt = count_stmt.where(Lead.status == filters.status)

        stmt = stmt.limit(filters.limit).offset(filters.offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def get_for_user(self, user: User, lead_id: uuid.UUID) -> Lead:
        """
        Fetch a single lead, applying RBAC scoping.

        Raises LeadNotFoundError if the lead does not exist OR is outside
        the user's scope — this is intentional to prevent existence leaking
        (spec §4 scenario 4.4).
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        if user.role in ("consultor", "comercial"):
            stmt = stmt.where(Lead.owner_id == user.id)

        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if result is None:
            raise LeadNotFoundError(lead_id)
        return result

    async def update_status(
        self, user: User, lead_id: uuid.UUID, new_status: str
    ) -> Lead:
        """
        Transition a Lead's status, enforcing the state machine rules.

        Raises:
            LeadNotFoundError:       lead not found or outside user's scope.
            InvalidTransitionError:  transition not permitted by LeadStatusMachine.
        """
        lead = await self.get_for_user(user, lead_id)

        try:
            LeadStatusMachine.assert_can_transition(lead.status, new_status)
        except DomainInvalidTransitionError as exc:
            allowed = LeadStatusMachine.valid_transitions.get(lead.status, set())
            logger.warning(
                "invalid_transition_attempted",
                extra={
                    "lead_id": str(lead_id),
                    "from": lead.status,
                    "to": new_status,
                    "actor_user_id": str(user.id),
                },
            )
            raise InvalidTransitionError(exc.from_status, exc.to_status, allowed) from exc

        old_status = lead.status
        lead.status = new_status
        await self.session.flush()
        await self.session.refresh(lead)

        logger.info(
            "lead_status_changed",
            extra={
                "lead_id": str(lead_id),
                "from_status": old_status,
                "to_status": new_status,
                "actor_user_id": str(user.id),
                "actor_role": user.role,
            },
        )
        return lead

    async def update(
        self, user: User, lead_id: uuid.UUID, payload: LeadUpdate
    ) -> Lead:
        """
        Partially update editable lead fields (name, phone, company, notes, role).

        RBAC scoping: consultor/comercial can only update leads they own.

        Raises:
            LeadNotFoundError: lead not found or outside user's scope.
        """
        lead = await self.get_for_user(user, lead_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def assign_owner(self, lead_id: uuid.UUID, owner_id: uuid.UUID) -> Lead:
        """
        Assign (or reassign) a Lead to a user.

        This is an admin-only operation. RBAC enforcement happens at the route layer
        via require_role('admin'). The service does NOT re-check roles here.

        Raises:
            LeadNotFoundError: lead not found (no RBAC scoping — admin can assign any lead).
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        lead = (await self.session.execute(stmt)).scalar_one_or_none()
        if lead is None:
            raise LeadNotFoundError(lead_id)

        lead.owner_id = owner_id
        await self.session.flush()
        await self.session.refresh(lead)
        return lead
