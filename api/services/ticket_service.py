"""
Ticket service — business logic for the Ticket aggregate.

Design principles (design §D2, §D3):
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- client_id_filter (from scope_to_client) is an explicit parameter on every
  read/write method — filtering happens here, not in middleware or route guards.
- 404 (TicketNotFoundError) is raised for out-of-scope tickets to avoid leaking
  existence across client boundaries (spec §404-on-out-of-scope policy).
- services flush; routes commit.
- Activity log entries are written by this service via activity_log_service.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.ticket import TicketCreate, TicketPatch, TicketUpdate
from api.services import activity_log_service
from api.services.exceptions import TicketNotFoundError
from database.models.ticket import Ticket

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


class TicketService:
    """
    Service layer for the Ticket aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Read ───────────────────────────────────────────────────────────────

    async def list_tickets(
        self,
        *,
        client_id_filter: uuid.UUID | None,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        priority: str | None = None,
    ) -> tuple[list[Ticket], int]:
        """
        Return a paginated list of tickets.

        When client_id_filter is not None (client_user branch), only tickets
        belonging to that client are returned. When None (internal branch), all
        tickets are returned.

        Optional filters: status, priority.
        """
        stmt = select(Ticket).order_by(Ticket.created_at.desc())
        count_stmt = select(func.count(Ticket.id))

        # Client-scope filter (design §D2)
        if client_id_filter is not None:
            stmt = stmt.where(Ticket.client_id == client_id_filter)
            count_stmt = count_stmt.where(Ticket.client_id == client_id_filter)

        if status is not None:
            stmt = stmt.where(Ticket.status == status)
            count_stmt = count_stmt.where(Ticket.status == status)

        if priority is not None:
            stmt = stmt.where(Ticket.priority == priority)
            count_stmt = count_stmt.where(Ticket.priority == priority)

        stmt = stmt.limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def get_ticket(
        self,
        ticket_id: uuid.UUID,
        *,
        client_id_filter: uuid.UUID | None,
    ) -> Ticket:
        """
        Fetch a single ticket by ID.

        Applies client_id_filter when provided. Out-of-scope or missing tickets
        raise TicketNotFoundError (→ HTTP 404, not 403) to prevent existence leaking.

        Raises:
            TicketNotFoundError: ticket not found or outside caller's client scope.
        """
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        if client_id_filter is not None:
            stmt = stmt.where(Ticket.client_id == client_id_filter)

        ticket = (await self.session.execute(stmt)).scalar_one_or_none()
        if ticket is None:
            raise TicketNotFoundError(ticket_id)
        return ticket

    # ─── Write ──────────────────────────────────────────────────────────────

    async def create_ticket(
        self,
        body: TicketCreate,
        *,
        client_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> Ticket:
        """
        Persist a new Ticket and write a ticket_opened activity log entry.

        client_id comes from scope_to_client — it is NOT taken from the request body.

        services flush; routes commit.

        Returns:
            The flushed Ticket ORM instance.
        """
        ticket = Ticket(
            client_id=client_id,
            service_id=body.service_id,
            title=body.title,
            priority=body.priority,
            body=body.body,
            status="pending",
            created_by_user_id=actor_user_id,
        )
        self.session.add(ticket)
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client_id,
            kind="ticket_opened",
            body=f"Ticket '{ticket.title}' opened (priority={ticket.priority})",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(ticket)
        logger.info(
            "ticket_created",
            extra={
                "ticket_id": str(ticket.id),
                "client_id": str(client_id),
                "actor_user_id": str(actor_user_id),
            },
        )
        return ticket

    async def update_ticket(
        self,
        ticket_id: uuid.UUID,
        body: TicketPatch,
        *,
        client_id_filter: uuid.UUID | None,
        actor_user_id: uuid.UUID,
    ) -> Ticket:
        """
        Patch allowed fields on a ticket.

        Clients (client_user) can update title, priority, body only.
        Status updates are handled by the internal PATCH /api/tickets/{id} endpoint (PR-3).

        Raises:
            TicketNotFoundError: ticket not found or outside caller's client scope.
        """
        ticket = await self.get_ticket(ticket_id, client_id_filter=client_id_filter)

        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ticket, field, value)

        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=ticket.client_id,
            kind="ticket_updated",
            body=f"Ticket '{ticket.title}' updated (fields: {list(update_data.keys())})",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(ticket)
        logger.info(
            "ticket_updated",
            extra={
                "ticket_id": str(ticket_id),
                "client_id": str(ticket.client_id),
                "actor_user_id": str(actor_user_id),
                "fields": list(update_data.keys()),
            },
        )
        return ticket

    async def update_ticket_internal(
        self,
        ticket_id: uuid.UUID,
        body: TicketUpdate,
        *,
        actor_user_id: uuid.UUID,
    ) -> Ticket:
        """
        Patch a ticket from an internal role (admin / consultor / comercial).

        Unlike update_ticket (client branch), this method:
        - Applies NO client_id_filter — internal users see any ticket.
        - Allows status and assigned_to_user_id changes.
        - Logs ticket_closed when status transitions to 'closed', otherwise
          ticket_updated for any other field change.

        services flush; routes commit.

        Raises:
            TicketNotFoundError: ticket not found.
        """
        ticket = await self.get_ticket(ticket_id, client_id_filter=None)

        update_data = body.model_dump(exclude_unset=True)
        previous_status = ticket.status

        for field, value in update_data.items():
            setattr(ticket, field, value)

        await self.session.flush()

        # Determine activity kind: ticket_closed takes precedence
        new_status = update_data.get("status")
        if new_status == "closed" and previous_status != "closed":
            activity_kind = "ticket_closed"
        else:
            activity_kind = "ticket_updated"

        await activity_log_service.append_activity(
            self.session,
            client_id=ticket.client_id,
            kind=activity_kind,
            body=f"Ticket '{ticket.title}' {activity_kind.replace('_', ' ')} (fields: {list(update_data.keys())})",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(ticket)
        logger.info(
            "ticket_updated_internal",
            extra={
                "ticket_id": str(ticket_id),
                "client_id": str(ticket.client_id),
                "actor_user_id": str(actor_user_id),
                "fields": list(update_data.keys()),
                "activity_kind": activity_kind,
            },
        )
        return ticket
