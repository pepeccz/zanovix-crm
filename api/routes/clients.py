"""
Client endpoints — authenticated CRUD + stage transitions.

Routes (all under prefix /api, registered in main.py):
  POST   /api/clients              — create (admin + comercial)
  GET    /api/clients              — list with filters, RBAC scoped
  GET    /api/clients/{id}         — detail with eager loads (contacts, services, activity)
  PATCH  /api/clients/{id}         — update metadata (admin + comercial)
  PATCH  /api/clients/{id}/stage   — stage transition (admin + comercial)

Design principles (design §8):
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in ClientService.
  - services flush; routes commit.
  - Error mapping: domain exceptions → HTTP status codes via handlers in api/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.schemas.client import (
    ClientCreate,
    ClientDetailResponse,
    ClientFilters,
    ClientListResponse,
    ClientRead,
    ClientStageChange,
    ClientUpdate,
)
from api.services.client_service import ClientService
from database.connection import get_async_session
from database.models.user import User

router = APIRouter(tags=["clients"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------


async def _get_session() -> AsyncSession:  # type: ignore[return]
    """Yield a per-request async database session."""
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# POST /api/clients  — admin + comercial
# ---------------------------------------------------------------------------


@router.post(
    "/clients",
    status_code=status.HTTP_201_CREATED,
    response_model=ClientRead,
    summary="Create a new client (admin + comercial)",
)
async def create_client(
    body: ClientCreate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ClientRead:
    """Create a new client. Returns 403 for consultor role."""
    service = ClientService(session)
    client = await service.create_client(body, current_user.id)
    await session.commit()
    return ClientRead.model_validate(client)


# ---------------------------------------------------------------------------
# GET /api/clients  — all authenticated roles, RBAC scoped
# ---------------------------------------------------------------------------


@router.get(
    "/clients",
    status_code=status.HTTP_200_OK,
    response_model=ClientListResponse,
    summary="List clients (authenticated, RBAC scoped)",
)
async def list_clients(
    request: Request,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ClientListResponse:
    """
    Return a paginated, filtered list of clients.

    RBAC:
    - admin      → all clients
    - consultor / comercial → own clients (owner_id == user.id)

    Filters: stage, owner_id, sector, q (ILIKE on name), limit, offset.
    limit > 200 → 400 (not 422) with error shape {\"error\": \"limit_exceeds_max\", \"max\": 200}.
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

    filters = ClientFilters(
        stage=request.query_params.get("stage"),
        owner_id=request.query_params.get("owner_id"),
        sector=request.query_params.get("sector"),
        q=request.query_params.get("q"),
        limit=int(raw_limit) if raw_limit and raw_limit.isdigit() else 50,
        offset=int(request.query_params.get("offset", 0)),
    )

    svc = ClientService(session)
    clients, total = await svc.list_clients(current_user, filters)

    return ClientListResponse(
        items=[ClientRead.model_validate(c) for c in clients],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )


# ---------------------------------------------------------------------------
# GET /api/clients/{id}  — all authenticated roles, RBAC scoped
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}",
    status_code=status.HTTP_200_OK,
    response_model=ClientDetailResponse,
    summary="Get client detail (contacts, services, recent activity)",
)
async def get_client(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> ClientDetailResponse:
    """
    Return full client detail with eager-loaded contacts, service stubs,
    and the last 20 activity log entries.

    consultor/comercial: only accessible if owner_id == user.id; otherwise 404.
    """
    svc = ClientService(session)
    client, recent_activity = await svc.get_client_detail(current_user, client_id)

    return ClientDetailResponse(
        id=client.id,
        created_at=client.created_at,
        updated_at=client.updated_at,
        name=client.name,
        sector=client.sector,
        size=client.size,
        region=client.region,
        owner_id=client.owner_id,
        stage=client.stage,
        entered_at=client.entered_at,
        mrr_cents=client.mrr_cents,
        lifetime_value_cents=client.lifetime_value_cents,
        contacts=client.contacts,
        services=client.services,
        recent_activity=recent_activity,
    )


# ---------------------------------------------------------------------------
# PATCH /api/clients/{id}  — admin + comercial
# ---------------------------------------------------------------------------


@router.patch(
    "/clients/{client_id}",
    status_code=status.HTTP_200_OK,
    response_model=ClientRead,
    summary="Update client metadata (admin + comercial)",
)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ClientRead:
    """Patch non-stage fields on a client. Stage changes must use the /stage endpoint."""
    svc = ClientService(session)
    client = await svc.update_client(current_user, client_id, body)
    await session.commit()
    return ClientRead.model_validate(client)


# ---------------------------------------------------------------------------
# PATCH /api/clients/{id}/stage  — admin + comercial
# ---------------------------------------------------------------------------


@router.patch(
    "/clients/{client_id}/stage",
    status_code=status.HTTP_200_OK,
    response_model=ClientRead,
    summary="Transition client stage (admin + comercial)",
)
async def change_client_stage(
    client_id: uuid.UUID,
    body: ClientStageChange,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ClientRead:
    """
    Advance a client's stage following ClientStageMachine rules.

    Invalid transitions return 409 with allowed transitions list.
    """
    svc = ClientService(session)
    client = await svc.change_stage(current_user, client_id, body.stage)
    await session.commit()
    return ClientRead.model_validate(client)
