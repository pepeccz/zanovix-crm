"""
Contact endpoints — nested under clients.

Routes (all under prefix /api, registered in main.py):
  GET    /api/clients/{client_id}/contacts              — list contacts
  POST   /api/clients/{client_id}/contacts              — create contact (admin + comercial)
  PATCH  /api/clients/{client_id}/contacts/{contact_id} — update contact (admin + comercial)
  DELETE /api/clients/{client_id}/contacts/{contact_id} — delete contact (admin only)

Design principles (design §8):
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in ContactService.
  - services flush; routes commit.
  - Error mapping: domain exceptions → HTTP status codes via handlers in api/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from api.services.contact_service import ContactService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["contacts"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/contacts  — all authenticated roles
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/contacts",
    status_code=status.HTTP_200_OK,
    response_model=list[ContactRead],
    summary="List contacts for a client",
)
async def list_contacts(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> list[ContactRead]:
    """Return all contacts for the given client, ordered by name."""
    svc = ContactService(session)
    contacts = await svc.list_contacts(client_id)
    return [ContactRead.model_validate(c) for c in contacts]


# ---------------------------------------------------------------------------
# POST /api/clients/{client_id}/contacts  — admin + comercial
# ---------------------------------------------------------------------------


@router.post(
    "/clients/{client_id}/contacts",
    status_code=status.HTTP_201_CREATED,
    response_model=ContactRead,
    summary="Create a contact under a client (admin + comercial)",
)
async def create_contact(
    client_id: uuid.UUID,
    body: ContactCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ContactRead:
    """
    Create a new contact under the specified client.

    Writes a 'contact_added' activity log entry on the parent client.
    """
    svc = ContactService(session)
    contact = await svc.create_contact(client_id, body, current_user.id)
    await session.commit()
    return ContactRead.model_validate(contact)


# ---------------------------------------------------------------------------
# PATCH /api/clients/{client_id}/contacts/{contact_id}  — admin + comercial
# ---------------------------------------------------------------------------


@router.patch(
    "/clients/{client_id}/contacts/{contact_id}",
    status_code=status.HTTP_200_OK,
    response_model=ContactRead,
    summary="Update a contact (admin + comercial)",
)
async def update_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    body: ContactUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ContactRead:
    """
    Patch a contact's fields.

    Writes a 'contact_updated' activity log entry on the parent client.
    """
    svc = ContactService(session)
    contact = await svc.update_contact(client_id, contact_id, body, current_user.id)
    await session.commit()
    return ContactRead.model_validate(contact)


# ---------------------------------------------------------------------------
# DELETE /api/clients/{client_id}/contacts/{contact_id}  — admin only
# ---------------------------------------------------------------------------


@router.delete(
    "/clients/{client_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a contact (admin only)",
)
async def delete_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin")),
) -> Response:
    """Delete a contact by ID. Admin only."""
    svc = ContactService(session)
    await svc.delete_contact(client_id, contact_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
