"""
Client self-service endpoints — /api/me/*.

All routes in this module are gated to the `client_user` role ONLY.
Internal roles (admin/comercial/consultor) receive HTTP 403 from scope_to_client.

Routes (all under prefix /api, registered in main.py):
  GET    /api/me/client                  — own client record
  GET    /api/me/services                — own services (filterable by state, type)
  GET    /api/me/services/{id}           — single service detail (includes diagnostic_json)
  GET    /api/me/services/{id}/diagnostic — assessment diagnostic (404 if no data)
  GET    /api/me/contacts                — own client contacts
  GET    /api/me/activity                — own client activity log
  GET    /api/me/messages                — own message thread (supports ?since=)
  POST   /api/me/messages                — send a message
  GET    /api/me/tickets                 — own tickets (filterable by status, priority)
  POST   /api/me/tickets                 — open a new ticket
  PATCH  /api/me/tickets/{id}            — update own ticket (title/priority/body only)

Design decisions honoured (design §D1, §D2, §D3, §D4):
  - scope_to_client enforces role=client_user; raises 403 for all other roles.
  - Service layer receives client_id_filter; out-of-scope reads → 404, never 403.
  - All writes commit at route level; services only flush.
  - Single router file for cohesion and ease of RLS audit.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.scope import scope_to_client
from api.schemas.activity_log import ActivityLogListResponse, ActivityLogRead
from api.schemas.client import ClientRead
from api.schemas.contact import ContactRead
from api.schemas.diagnostic import DiagnosticRead
from api.schemas.message import MessageCreate, MessageListResponse, MessageOut
from api.schemas.service import ServiceListResponse, ServiceRead
from api.schemas.ticket import TicketCreate, TicketListResponse, TicketOut, TicketPatch
from api.services.activity_log_service import list_activity
from api.services.contact_service import ContactService
from api.services.diagnostic_service import DiagnosticService
from api.services.message_service import MessageService
from api.services.service_service import ServiceService
from api.services.ticket_service import TicketService
from database.connection import get_async_session
from database.models.client import Client
from database.models.user import User

router = APIRouter(tags=["me"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/me/client — own client record
# ---------------------------------------------------------------------------


@router.get(
    "/me/client",
    status_code=status.HTTP_200_OK,
    response_model=ClientRead,
    summary="Get own client record (client_user only)",
)
async def get_my_client(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> ClientRead:
    """
    Return the client record linked to the authenticated client_user.

    Raises 404 if the client no longer exists (e.g. deleted after token issued).
    """
    _current_user, client_id = scope

    stmt = select(Client).where(Client.id == client_id)
    client = (await session.execute(stmt)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientRead.model_validate(client)


# ---------------------------------------------------------------------------
# GET /api/me/services — own services
# ---------------------------------------------------------------------------


@router.get(
    "/me/services",
    status_code=status.HTTP_200_OK,
    response_model=ServiceListResponse,
    summary="List own services (client_user only)",
)
async def list_my_services(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    state: str | None = Query(default=None),
    type: str | None = Query(default=None),
) -> ServiceListResponse:
    """Return paginated services for the authenticated client_user's client."""
    _current_user, client_id = scope

    svc = ServiceService(session)
    services, total = await svc.list_for_client(
        client_id_filter=client_id,
        limit=limit,
        offset=offset,
        state=state,
        type=type,
    )
    return ServiceListResponse(
        items=[ServiceRead.model_validate(s) for s in services],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/me/services/{id} — single service detail
# ---------------------------------------------------------------------------


@router.get(
    "/me/services/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    summary="Get a single service detail (client_user only)",
)
async def get_my_service(
    service_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> ServiceRead:
    """
    Return a single service with milestones and diagnostic_json.

    Returns 404 if the service does not belong to the authenticated client.
    """
    _current_user, client_id = scope

    svc = ServiceService(session)
    service = await svc.get_for_client(service_id, client_id_filter=client_id)
    return ServiceRead.model_validate(service)


# ---------------------------------------------------------------------------
# GET /api/me/services/{id}/diagnostic — assessment diagnostic
# ---------------------------------------------------------------------------


@router.get(
    "/me/services/{service_id}/diagnostic",
    status_code=status.HTTP_200_OK,
    response_model=DiagnosticRead,
    summary="Get assessment diagnostic for a service (client_user only)",
)
async def get_my_service_diagnostic(
    service_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> DiagnosticRead:
    """
    Return the diagnostic JSON for a service with type=assessment.

    Returns 404 when:
    - The service does not belong to the authenticated client.
    - The service type is not 'assessment'.
    - The service has no diagnostic data (diagnostic_json IS NULL).
    """
    _current_user, client_id = scope

    diag_svc = DiagnosticService(session)
    diagnostic = await diag_svc.get_diagnostic(service_id, client_id_filter=client_id)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail="No diagnostic data available for this service")

    return diagnostic


# ---------------------------------------------------------------------------
# GET /api/me/contacts — own contacts
# ---------------------------------------------------------------------------


@router.get(
    "/me/contacts",
    status_code=status.HTTP_200_OK,
    response_model=list[ContactRead],
    summary="List own contacts (client_user only)",
)
async def list_my_contacts(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> list[ContactRead]:
    """Return all contacts belonging to the authenticated client_user's client."""
    _current_user, client_id = scope

    contact_svc = ContactService(session)
    contacts = await contact_svc.list_contacts(client_id)
    return [ContactRead.model_validate(c) for c in contacts]


# ---------------------------------------------------------------------------
# GET /api/me/activity — own activity log
# ---------------------------------------------------------------------------


@router.get(
    "/me/activity",
    status_code=status.HTTP_200_OK,
    response_model=ActivityLogListResponse,
    summary="List own activity log entries (client_user only)",
)
async def list_my_activity(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> ActivityLogListResponse:
    """Return paginated activity log entries scoped to the authenticated client."""
    _current_user, client_id = scope

    items, total = await list_activity(
        session,
        limit=limit,
        offset=offset,
        client_id=client_id,
    )
    return ActivityLogListResponse(
        items=[ActivityLogRead.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/me/messages — own message thread
# ---------------------------------------------------------------------------


@router.get(
    "/me/messages",
    status_code=status.HTTP_200_OK,
    response_model=MessageListResponse,
    summary="List own messages (client_user only, supports ?since= polling)",
)
async def list_my_messages(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    since: datetime | None = Query(
        default=None,
        description="ISO-8601 datetime — return only messages newer than this timestamp.",
    ),
) -> MessageListResponse:
    """
    Return paginated messages for the authenticated client.

    Supports polling via the `since` query parameter (spec §messages-polling).
    The frontend polls every 10 000 ms and passes the last message timestamp as `since`.
    """
    _current_user, client_id = scope

    msg_svc = MessageService(session)
    messages, total = await msg_svc.list_messages(
        client_id,
        limit=limit,
        offset=offset,
        since=since,
    )
    return MessageListResponse(
        items=[MessageOut.model_validate(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# POST /api/me/messages — send a message
# ---------------------------------------------------------------------------


@router.post(
    "/me/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageOut,
    summary="Send a message (client_user only)",
)
async def send_my_message(
    body: MessageCreate,
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> MessageOut:
    """
    Send a new message in the client thread.

    Body must be 1–4000 characters (validated by Pydantic — returns 422 if invalid).
    Activity kind `message_sent` is logged automatically.
    """
    current_user, client_id = scope

    msg_svc = MessageService(session)
    message = await msg_svc.create_message(
        body,
        client_id=client_id,
        sender_user_id=current_user.id,
    )
    await session.commit()
    return MessageOut.model_validate(message)


# ---------------------------------------------------------------------------
# GET /api/me/tickets — own tickets
# ---------------------------------------------------------------------------


@router.get(
    "/me/tickets",
    status_code=status.HTTP_200_OK,
    response_model=TicketListResponse,
    summary="List own tickets (client_user only)",
)
async def list_my_tickets(
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    ticket_status: str | None = Query(default=None, alias="status", description="Filter by ticket status"),
    priority: str | None = Query(default=None, description="Filter by ticket priority"),
) -> TicketListResponse:
    """Return paginated tickets for the authenticated client."""
    _current_user, client_id = scope

    ticket_svc = TicketService(session)
    tickets, total = await ticket_svc.list_tickets(
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
# POST /api/me/tickets — open a ticket
# ---------------------------------------------------------------------------


@router.post(
    "/me/tickets",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketOut,
    summary="Open a new support ticket (client_user only)",
)
async def create_my_ticket(
    body: TicketCreate,
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> TicketOut:
    """
    Open a new support ticket for the authenticated client.

    client_id is injected automatically from scope_to_client — it is NOT
    taken from the request body. Activity kind `ticket_opened` is logged.
    """
    current_user, client_id = scope

    ticket_svc = TicketService(session)
    ticket = await ticket_svc.create_ticket(
        body,
        client_id=client_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return TicketOut.model_validate(ticket)


# ---------------------------------------------------------------------------
# PATCH /api/me/tickets/{id} — update own ticket (title/priority/body only)
# ---------------------------------------------------------------------------


@router.patch(
    "/me/tickets/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketOut,
    summary="Update own ticket fields (client_user only — title/priority/body only)",
)
async def update_my_ticket(
    ticket_id: uuid.UUID,
    body: TicketPatch,
    session: AsyncSession = Depends(_get_session),
    scope: tuple[User, uuid.UUID] = Depends(scope_to_client),
) -> TicketOut:
    """
    Update title, priority, or body on an own ticket.

    Status changes are NOT allowed here — they are reserved for internal roles
    via PATCH /api/tickets/{id} (PR-3).

    Returns 404 if the ticket does not belong to the authenticated client.
    """
    current_user, client_id = scope

    ticket_svc = TicketService(session)
    ticket = await ticket_svc.update_ticket(
        ticket_id,
        body,
        client_id_filter=client_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return TicketOut.model_validate(ticket)
