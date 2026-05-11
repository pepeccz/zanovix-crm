"""
Service endpoints — list, detail, create (nested under client), update, state transition.

Routes (all under prefix /api, registered in main.py):
  GET    /api/services              — list with filters (admin/comercial all; consultor own)
  GET    /api/services/{id}         — detail with milestones nested
  POST   /api/clients/{id}/services — create under client (admin + comercial)
  PATCH  /api/services/{id}         — update metadata (admin + comercial + consultor own)
  PATCH  /api/services/{id}/state   — state transition (admin + comercial + consultor own)

Design principles (design §8):
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in ServiceService.
  - services flush; routes commit.
  - Error mapping: domain exceptions → HTTP status codes via handlers in api/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.schemas.service import (
    ServiceCreate,
    ServiceFilters,
    ServiceListResponse,
    ServiceRead,
    ServiceStateChange,
    ServiceUpdate,
)
from api.services.service_service import ServiceService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["services"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# GET /api/services  — all authenticated roles, RBAC scoped
# ---------------------------------------------------------------------------


@router.get(
    "/services",
    status_code=status.HTTP_200_OK,
    response_model=ServiceListResponse,
    summary="List services (authenticated, RBAC scoped)",
)
async def list_services(
    request: Request,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ServiceListResponse:
    """
    Return a paginated, filtered list of services.

    RBAC:
    - admin / comercial → all services
    - consultor         → only services where owner_id == user.id

    Filters: client_id, owner_id, state, type, limit, offset.
    limit > 200 → 400 with error shape {\"error\": \"limit_exceeds_max\", \"max\": 200}.
    """
    raw_limit = request.query_params.get("limit")
    if raw_limit is not None:
        try:
            if int(raw_limit) > 200:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "limit_exceeds_max", "max": 200},
                )
        except ValueError:
            pass  # let Pydantic handle non-integer values with 422

    filters = ServiceFilters(
        client_id=request.query_params.get("client_id"),
        owner_id=request.query_params.get("owner_id"),
        state=request.query_params.get("state"),
        type=request.query_params.get("type"),
        limit=int(raw_limit) if raw_limit and raw_limit.isdigit() else 50,
        offset=int(request.query_params.get("offset", 0)),
    )

    svc = ServiceService(session)
    services, total = await svc.list_services(current_user, filters)

    return ServiceListResponse(
        items=[ServiceRead.model_validate(s) for s in services],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )


# ---------------------------------------------------------------------------
# GET /api/services/{id}  — all authenticated roles (RBAC enforced in service)
# ---------------------------------------------------------------------------


@router.get(
    "/services/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    summary="Get service detail with milestones",
)
async def get_service(
    service_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ServiceRead:
    """
    Return full service detail with nested milestones.

    consultor: only accessible if owner_id == user.id; otherwise 404.
    """
    svc = ServiceService(session)
    service = await svc.get_service_detail(current_user, service_id)
    return ServiceRead.model_validate(service)


# ---------------------------------------------------------------------------
# POST /api/clients/{client_id}/services  — admin + comercial
# ---------------------------------------------------------------------------


@router.post(
    "/clients/{client_id}/services",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceRead,
    summary="Create a service under a client (admin + comercial)",
)
async def create_service(
    client_id: uuid.UUID,
    body: ServiceCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ServiceRead:
    """
    Create a new service under the given client.

    Returns 422 if the client's stage is 'lost' (REQ-16).
    The body client_id is overridden with the path client_id.
    """
    # Override body client_id with path param to keep the nested-resource semantic
    body_with_client = body.model_copy(update={"client_id": client_id})
    svc = ServiceService(session)
    service = await svc.create_service(body_with_client, current_user.id)
    await session.commit()
    return ServiceRead.model_validate(service)


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}  — admin + comercial + consultor (own service)
# ---------------------------------------------------------------------------


@router.patch(
    "/services/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    summary="Update service metadata (admin + comercial + consultor on own service)",
)
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ServiceRead:
    """
    Patch general (non-state) fields on a service.

    consultor: only permitted on own services (owner_id == user.id); otherwise 404.
    """
    svc = ServiceService(session)
    service = await svc.update_service(current_user, service_id, body)
    await session.commit()
    return ServiceRead.model_validate(service)


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}/state  — admin + comercial + consultor (own service)
# ---------------------------------------------------------------------------


@router.patch(
    "/services/{service_id}/state",
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    summary="Transition service state (admin + comercial + consultor on own service)",
)
async def change_service_state(
    service_id: uuid.UUID,
    body: ServiceStateChange,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ServiceRead:
    """
    Advance a service's state following ServiceStateMachine rules.

    consultor: only permitted on own services; otherwise 404.
    Invalid transitions return 409 with allowed transitions list.
    """
    svc = ServiceService(session)
    service = await svc.change_state(current_user, service_id, body.state)
    await session.commit()
    return ServiceRead.model_validate(service)
