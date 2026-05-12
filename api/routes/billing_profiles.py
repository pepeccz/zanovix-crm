"""
BillingProfile endpoints.

Routes (all under prefix /api, registered in main.py):
  POST   /api/clients/{client_id}/billing-profiles        — create (admin + comercial)
  GET    /api/clients/{client_id}/billing-profiles        — list (admin + comercial)
  GET    /api/billing-profiles/{id}                       — get (admin + comercial)
  PATCH  /api/billing-profiles/{id}                       — update (admin + comercial)
  DELETE /api/billing-profiles/{id}                       — delete (admin + comercial)
  PATCH  /api/billing-profiles/{id}/default               — set default (admin + comercial)

Design principles:
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in BillingProfileService.
  - services flush; routes commit.
  - Error mapping: domain exceptions → HTTP status codes via handlers in api/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.schemas.billing_profile import BillingProfileCreate, BillingProfileRead, BillingProfileUpdate
from api.services.billing_profile_service import BillingProfileService
from database.connection import get_async_session
from database.models.user import User

nested_router = APIRouter(tags=["billing-profiles"])
flat_router = APIRouter(tags=["billing-profiles"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# POST /api/clients/{client_id}/billing-profiles  — admin + comercial
# ---------------------------------------------------------------------------


@nested_router.post(
    "/clients/{client_id}/billing-profiles",
    status_code=status.HTTP_201_CREATED,
    response_model=BillingProfileRead,
    summary="Create a billing profile for a client (admin + comercial)",
)
async def create_billing_profile(
    client_id: uuid.UUID,
    body: BillingProfileCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> BillingProfileRead:
    """Create a new billing profile under the specified client."""
    svc = BillingProfileService(session)
    profile = await svc.create_for_client(client_id, body)
    await session.commit()
    return BillingProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/billing-profiles  — admin + comercial
# ---------------------------------------------------------------------------


@nested_router.get(
    "/clients/{client_id}/billing-profiles",
    status_code=status.HTTP_200_OK,
    response_model=list[BillingProfileRead],
    summary="List billing profiles for a client (admin + comercial)",
)
async def list_billing_profiles(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> list[BillingProfileRead]:
    """Return all billing profiles for the client, default first."""
    svc = BillingProfileService(session)
    profiles = await svc.list_for_client(client_id)
    return [BillingProfileRead.model_validate(p) for p in profiles]


# ---------------------------------------------------------------------------
# GET /api/billing-profiles/{id}  — admin + comercial
# ---------------------------------------------------------------------------


@flat_router.get(
    "/billing-profiles/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=BillingProfileRead,
    summary="Get a billing profile by ID (admin + comercial)",
)
async def get_billing_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> BillingProfileRead:
    """Fetch a single billing profile by ID."""
    svc = BillingProfileService(session)
    profile = await svc.get(profile_id)
    return BillingProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# PATCH /api/billing-profiles/{id}  — admin + comercial
# ---------------------------------------------------------------------------


@flat_router.patch(
    "/billing-profiles/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=BillingProfileRead,
    summary="Update a billing profile (admin + comercial)",
)
async def update_billing_profile(
    profile_id: uuid.UUID,
    body: BillingProfileUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> BillingProfileRead:
    """Partially update a billing profile's fields."""
    svc = BillingProfileService(session)
    profile = await svc.update(profile_id, body)
    await session.commit()
    return BillingProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# DELETE /api/billing-profiles/{id}  — admin + comercial
# ---------------------------------------------------------------------------


@flat_router.delete(
    "/billing-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a billing profile (admin + comercial)",
)
async def delete_billing_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> Response:
    """
    Delete a billing profile.

    Returns 409 if the profile is the client's only billing profile.
    Automatically promotes the oldest sibling to default if the deleted profile
    was the default and siblings exist.
    """
    svc = BillingProfileService(session)
    await svc.delete(profile_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# PATCH /api/billing-profiles/{id}/default  — admin + comercial
# ---------------------------------------------------------------------------


@flat_router.patch(
    "/billing-profiles/{profile_id}/default",
    status_code=status.HTTP_200_OK,
    response_model=BillingProfileRead,
    summary="Set a billing profile as default (admin + comercial)",
)
async def set_default_billing_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> BillingProfileRead:
    """Promote the specified profile to default; demote all others in the same client."""
    svc = BillingProfileService(session)
    profile = await svc.set_default(profile_id)
    await session.commit()
    return BillingProfileRead.model_validate(profile)
