"""
Lead endpoints — public intake + authenticated CRUD.

Routes (all under prefix /api, registered in main.py):
  POST   /api/leads              — public, rate-limited
  GET    /api/leads              — auth required (RBAC scoped)
  PATCH  /api/leads/{id}/status  — auth required (state machine)
  PATCH  /api/leads/{id}/assign  — admin only

Design principles (design §4.2):
  - Routes are thin: validate HTTP input, call service, serialize response.
  - No business logic here — all lives in LeadService.
  - Error mapping: domain exceptions → HTTP status codes via error handlers
    registered in main.py (see api/errors.py).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.domain.payload_sanitizer import build_raw_payload
from api.middleware.rate_limit import enforce_lead_post_rate_limit
from api.schemas.client import ClientRead
from api.schemas.convert_lead import ConvertLeadBody
from api.schemas.lead import (
    LeadAssign,
    LeadCreate,
    LeadFilters,
    LeadListResponse,
    LeadRead,
    LeadStatusUpdate,
    LeadUpdate,
)
from api.services.client_service import ClientService
from api.services.exceptions import InvalidTransitionError, LeadNotFoundError
from api.services.lead_service import LeadService
from database.connection import get_async_session
from database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["leads"])


# ---------------------------------------------------------------------------
# Internal: session dependency
# ---------------------------------------------------------------------------

async def _get_session() -> AsyncSession:  # type: ignore[return]
    """
    FastAPI dependency that yields a database session.

    Wraps get_async_session() (context manager) as a proper async generator
    so FastAPI can inject and close it automatically.
    """
    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# POST /api/leads  — public, rate-limited
# ---------------------------------------------------------------------------


@router.post(
    "/leads",
    status_code=status.HTTP_201_CREATED,
    response_model=LeadRead,
    summary="Submit a new lead (public)",
)
async def create_lead(
    request: Request,
    payload: LeadCreate,
    session: AsyncSession = Depends(_get_session),
    _rate_limit: None = Depends(enforce_lead_post_rate_limit),
) -> LeadRead:
    """
    Public intake endpoint — no authentication required.

    Rate-limited: 20 requests / 60 seconds per IP (spec §6).
    raw_payload is stored internally but EXCLUDED from the response (spec §7.4).
    """
    raw_payload = build_raw_payload(request, payload.model_dump())
    service = LeadService(session)
    lead = await service.create(payload, raw_payload)
    await session.commit()
    return LeadRead.model_validate(lead)


# ---------------------------------------------------------------------------
# GET /api/leads  — authenticated, RBAC scoped
# ---------------------------------------------------------------------------


@router.get(
    "/leads",
    status_code=status.HTTP_200_OK,
    response_model=LeadListResponse,
    summary="List leads (authenticated, RBAC scoped)",
)
async def list_leads(
    request: Request,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> LeadListResponse:
    """
    Return a paginated, filtered list of leads.

    RBAC:
    - admin:      sees all leads
    - consultor / comercial: sees only leads where owner_id == own id

    Filters (all optional, AND-combined): vertical, channel, status.
    Pagination: limit (default 50, max 200), offset (default 0).

    Decision #2: limit > 200 → 400 (not silently clamped).
    LeadFilters.limit already has le=200 via Pydantic — FastAPI will return
    422 for values > 200. We additionally check with an explicit 400 to match
    the spec error shape {"error":"limit_exceeds_max","max":200}.
    """
    # Read raw query params to intercept limit > 200 before Pydantic binding
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

    # Bind to LeadFilters (validates remaining params)
    filters = LeadFilters(
        vertical=request.query_params.get("vertical"),
        channel=request.query_params.get("channel"),
        status=request.query_params.get("status"),
        limit=int(raw_limit) if raw_limit and raw_limit.isdigit() else 50,
        offset=int(request.query_params.get("offset", 0)),
    )

    service = LeadService(session)
    leads, total = await service.list_for_user(current_user, filters)

    return LeadListResponse(
        items=[LeadRead.model_validate(lead) for lead in leads],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )


# ---------------------------------------------------------------------------
# GET /api/leads/{id}  — authenticated, RBAC scoped
# ---------------------------------------------------------------------------


@router.get(
    "/leads/{lead_id}",
    status_code=status.HTTP_200_OK,
    response_model=LeadRead,
    summary="Get a single lead (authenticated, RBAC scoped)",
)
async def get_lead(
    lead_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> LeadRead:
    """
    Return a single lead by ID.

    RBAC:
    - admin: sees any lead
    - consultor / comercial: sees only leads where owner_id == own id; otherwise 404
    """
    service = LeadService(session)
    lead = await service.get_for_user(current_user, lead_id)
    if lead is None:
        raise LeadNotFoundError(str(lead_id))
    return LeadRead.model_validate(lead)


# ---------------------------------------------------------------------------
# PATCH /api/leads/{id}  — authenticated, editable fields (role, name, phone, etc.)
# ---------------------------------------------------------------------------


@router.patch(
    "/leads/{lead_id}",
    status_code=status.HTTP_200_OK,
    response_model=LeadRead,
    summary="Update editable lead fields (authenticated, RBAC scoped)",
)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> LeadRead:
    """
    Partially update a lead's editable fields (name, phone, company, notes, role).

    Does NOT accept status changes — use PATCH /leads/{id}/status for those.
    RBAC: consultor/comercial can only update leads they own (404 on out-of-scope).
    """
    service = LeadService(session)
    try:
        lead = await service.update(current_user, lead_id, body)
    except LeadNotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")
    await session.commit()
    return LeadRead.model_validate(lead)


# ---------------------------------------------------------------------------
# PATCH /api/leads/{id}/status  — authenticated, state machine enforced
# ---------------------------------------------------------------------------


@router.patch(
    "/leads/{lead_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=LeadRead,
    summary="Update lead status (authenticated, state machine)",
)
async def update_lead_status(
    lead_id: uuid.UUID,
    body: LeadStatusUpdate,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(get_current_user),
) -> LeadRead:
    """
    Transition a lead's status following the allowed state machine.

    Valid transitions:
      new → contacted | disqualified
      contacted → qualified | disqualified
      qualified → converted | disqualified
      disqualified → (terminal)
      converted → (terminal)

    RBAC: consultor/comercial can only update leads they own.
    A lead outside the user's scope returns 404 (not 403) — spec §4 scenario 4.4.
    """
    service = LeadService(session)
    try:
        lead = await service.update_status(current_user, lead_id, body.status)
    except LeadNotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "invalid_transition",
                "from": exc.from_status,
                "to": exc.to_status,
                "allowed": sorted(exc.allowed_transitions),
            },
        )
    await session.commit()
    return LeadRead.model_validate(lead)


# ---------------------------------------------------------------------------
# PATCH /api/leads/{id}/assign  — admin only (decision #4)
# ---------------------------------------------------------------------------


@router.patch(
    "/leads/{lead_id}/assign",
    status_code=status.HTTP_200_OK,
    response_model=LeadRead,
    summary="Assign a lead to a user (admin only)",
)
async def assign_lead(
    lead_id: uuid.UUID,
    body: LeadAssign,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin")),
) -> LeadRead:
    """
    Assign (or re-assign) a lead's owner_id.

    Admin-only (decision #4). Non-admin roles receive 403.
    If owner_id does not correspond to an existing user → 404.
    If lead_id does not correspond to an existing lead → 404.
    """
    # Verify owner_id exists in users table
    result = await session.execute(
        select(User).where(User.id == body.owner_id)
    )
    owner = result.scalar_one_or_none()
    if owner is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "owner_user_not_found"},
        )

    service = LeadService(session)
    try:
        lead = await service.assign_owner(lead_id, body.owner_id)
    except LeadNotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")

    await session.commit()
    return LeadRead.model_validate(lead)


# ---------------------------------------------------------------------------
# POST /api/leads/{id}/convert  — admin + comercial (REQ-13)
# ---------------------------------------------------------------------------


@router.post(
    "/leads/{lead_id}/convert",
    status_code=status.HTTP_201_CREATED,
    response_model=ClientRead,
    summary="Convert a qualified lead into a client (admin + comercial)",
)
async def convert_lead(
    lead_id: uuid.UUID,
    body: ConvertLeadBody,
    session: AsyncSession = Depends(_get_session),
    current_user: User = Depends(require_role("admin", "comercial")),
) -> ClientRead:
    """
    Atomically convert a qualified lead to a client (REQ-13).

    - 404 if lead not found.
    - 422 if lead.status != 'qualified'.
    - 409 if lead already converted (returns existing client_id).
    - 201 + ClientRead on success.

    Body fields override lead data; absent fields fall back to lead.company / lead.name.
    """
    svc = ClientService(session)
    client = await svc.convert_from_lead(lead_id, body, current_user.id)
    await session.commit()
    return ClientRead.model_validate(client)
