"""
Internal ticket endpoints — admin / consultor / comercial.

Routes (all under prefix /api, registered in main.py):
  GET    /api/clients/{client_id}/tickets          — list tickets for a client
  GET    /api/tickets/{ticket_id}                  — get a single ticket
  PATCH  /api/tickets/{ticket_id}                  — update ticket (status, assignment, etc.)

RBAC:
  - GET endpoints:  admin / consultor / comercial
  - PATCH endpoint: admin / consultor — full update including status
                    comercial        — partial update (status change blocked at route level)

Design principles (design §D2, §D3):
  - client_id_filter=None for all internal endpoints (no client scope restriction).
  - Services flush; routes commit.
  - Error mapping delegated to domain error handlers in api/errors.py.
  - Comercial cannot change ticket status (spec §RBAC invariants).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.schemas.ticket import TicketListResponse, TicketOut, TicketUpdate
from api.services.ticket_service import TicketService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["tickets"])

MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/tickets  — admin / consultor / comercial
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/tickets",
    status_code=status.HTTP_200_OK,
    response_model=TicketListResponse,
    summary="List tickets for a client (internal roles only)",
)
async def list_client_tickets(
    client_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "consultor", "comercial")),
) -> TicketListResponse:
    """
    Return a paginated list of tickets for the specified client.

    Supports optional query filters: status, priority.
    limit > 200 → 400 with {success: false, error_code: HTTP_400} envelope.

    Internal roles see all tickets for the client — no client_id_filter applied.
    """
    raw_limit = request.query_params.get("limit")
    if raw_limit is not None:
        try:
            if int(raw_limit) > MAX_LIMIT:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "limit_exceeds_max", "max": MAX_LIMIT},
                )
        except ValueError:
            pass  # let Pydantic handle non-integer values with 422

    limit = int(raw_limit) if raw_limit and raw_limit.isdigit() else 50
    offset = int(request.query_params.get("offset", 0))
    ticket_status = request.query_params.get("status")
    priority = request.query_params.get("priority")

    svc = TicketService(session)
    tickets, total = await svc.list_tickets(
        client_id_filter=client_id,
        limit=limit,
        offset=offset,
        status=ticket_status,
        priority=priority,
    )

    return TicketListResponse(
        items=[TicketOut.model_validate(t) for t in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/tickets/{ticket_id}  — admin / consultor / comercial
# ---------------------------------------------------------------------------


@router.get(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketOut,
    summary="Get a ticket by ID (internal roles only)",
)
async def get_ticket(
    ticket_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "consultor", "comercial")),
) -> TicketOut:
    """
    Return a single ticket by ID. Any internal role may read any ticket.

    Returns 404 if the ticket does not exist.
    """
    svc = TicketService(session)
    ticket = await svc.get_ticket(ticket_id, client_id_filter=None)
    return TicketOut.model_validate(ticket)


# ---------------------------------------------------------------------------
# PATCH /api/tickets/{ticket_id}  — admin + consultor (full); comercial (no status)
# ---------------------------------------------------------------------------


@router.patch(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketOut,
    summary="Update a ticket (internal roles; comercial cannot change status)",
)
async def update_ticket_internal(
    ticket_id: uuid.UUID,
    body: TicketUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "consultor", "comercial")),
) -> TicketOut:
    """
    Patch a ticket's fields.

    Admin and consultor can change any field including status and assigned_to_user_id.
    Comercial can change title, priority, body, and assigned_to — but NOT status.

    Logs ticket_closed when status transitions to 'closed'; ticket_updated otherwise.
    """
    if current_user.role == "comercial" and body.status is not None:
        raise HTTPException(
            status_code=403,
            detail="Comercial role cannot change ticket status",
        )

    svc = TicketService(session)
    ticket = await svc.update_ticket_internal(
        ticket_id,
        body,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return TicketOut.model_validate(ticket)
