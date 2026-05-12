"""
Internal message endpoints — admin / consultor / comercial.

Routes (all under prefix /api, registered in main.py):
  GET    /api/clients/{client_id}/messages  — list message thread for a client
  POST   /api/clients/{client_id}/messages  — admin/consultor replies to client

RBAC:
  - GET:  admin / consultor / comercial
  - POST: admin / consultor only (comercial cannot send messages — spec §RBAC invariants)

Design principles (design §D2, §D9):
  - Internal routes pass client_id directly — no client_id_filter restriction.
  - sender_user_id = current_user.id (set by route, not by client body).
  - services flush; routes commit.
  - Error mapping delegated to domain error handlers in api/errors.py.
  - client_user calling GET /api/clients/{id}/messages → 403 via require_role guard.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.schemas.message import MessageCreate, MessageListResponse, MessageOut
from api.services.message_service import MessageService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["messages"])

MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/messages  — admin / consultor / comercial
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=MessageListResponse,
    summary="List messages for a client (internal roles only)",
)
async def list_client_messages(
    client_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "consultor", "comercial")),
) -> MessageListResponse:
    """
    Return a paginated message thread for the specified client.

    limit > 200 → 400 with {success: false, error_code: HTTP_400} envelope.

    Internal roles see all messages for the client — no client_id_filter applied.
    client_user callers receive 403 from the require_role guard (spec §client_user cannot
    access internal endpoint).
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

    svc = MessageService(session)
    messages, total = await svc.list_messages(
        client_id,
        limit=limit,
        offset=offset,
    )

    return MessageListResponse(
        items=[MessageOut.model_validate(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# POST /api/clients/{client_id}/messages  — admin / consultor only
# ---------------------------------------------------------------------------


@router.post(
    "/clients/{client_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageOut,
    summary="Send a message to a client thread (admin / consultor only)",
)
async def create_client_message(
    client_id: uuid.UUID,
    body: MessageCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "consultor")),
) -> MessageOut:
    """
    Create a new message in the client's thread.

    sender_user_id is always set to the authenticated internal user's ID.
    Comercial role is excluded — they can read but not reply to clients.
    """
    svc = MessageService(session)
    message = await svc.create_message(
        body,
        client_id=client_id,
        sender_user_id=current_user.id,
    )
    await session.commit()
    return MessageOut.model_validate(message)
