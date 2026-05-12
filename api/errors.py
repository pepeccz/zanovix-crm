"""
Domain exception → HTTP response mapping.

Registers FastAPI exception handlers for domain-level exceptions raised by
the service layer. These handlers live here (not in shared/) because they are
specific to this application's domain model.

Handlers registered:
  LeadNotFoundError             → 404
  InvalidTransitionError        → 409 with allowed_transitions in body
  RateLimitExceededError        → 429 (fallback; normally HTTPException(429) raised directly)
  ClientNotFoundError           → 404
  ServiceNotFoundError          → 404
  ContactNotFoundError          → 404
  MilestoneNotFoundError        → 404
  CannotCreateOnLostClientError → 422 {"error": "client_is_lost"}
  LeadAlreadyConvertedError     → 409 {"error": "already_converted", "client_id": ...}
  LeadNotQualifiedError         → 422 {"error": "lead_not_qualified", "current_status": ...}
  RBACForbiddenError            → 403
  TicketNotFoundError           → 404
  MessageNotFoundError          → 404

Usage:
    from api.errors import register_domain_error_handlers
    register_domain_error_handlers(app)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.services.exceptions import (
    BillingProfileNotFoundError,
    CannotCreateOnLostClientError,
    CannotDeleteOnlyDefaultError,
    ClientNotFoundError,
    ContactNotFoundError,
    DuplicateTaxIdError,
    InvalidTransitionError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    LeadNotQualifiedError,
    MessageNotFoundError,
    MilestoneNotFoundError,
    RateLimitExceededError,
    RBACForbiddenError,
    ServiceNotFoundError,
    TicketNotFoundError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lead-domain handlers (existing)
# ---------------------------------------------------------------------------


async def _lead_not_found_handler(request: Request, exc: LeadNotFoundError) -> JSONResponse:
    logger.info(
        "lead_not_found",
        extra={"lead_id": str(exc.lead_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Lead not found"},
    )


async def _invalid_transition_handler(
    request: Request, exc: InvalidTransitionError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "invalid_transition",
            "from": exc.from_status,
            "to": exc.to_status,
            "allowed": sorted(exc.allowed_transitions),
        },
    )


async def _rate_limit_handler(
    request: Request, exc: RateLimitExceededError
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. Try again in {exc.retry_after_seconds} seconds."},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


# ---------------------------------------------------------------------------
# Client-domain handlers (crm-core-domain slice)
# ---------------------------------------------------------------------------


async def _client_not_found_handler(request: Request, exc: ClientNotFoundError) -> JSONResponse:
    logger.info(
        "client_not_found",
        extra={"client_id": str(exc.client_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Client not found"},
    )


async def _service_not_found_handler(request: Request, exc: ServiceNotFoundError) -> JSONResponse:
    logger.info(
        "service_not_found",
        extra={"service_id": str(exc.service_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Service not found"},
    )


async def _contact_not_found_handler(request: Request, exc: ContactNotFoundError) -> JSONResponse:
    logger.info(
        "contact_not_found",
        extra={"contact_id": str(exc.contact_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Contact not found"},
    )


async def _milestone_not_found_handler(
    request: Request, exc: MilestoneNotFoundError
) -> JSONResponse:
    logger.info(
        "milestone_not_found",
        extra={
            "service_id": str(exc.service_id),
            "n": str(exc.n),
            "path": str(request.url.path),
        },
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Milestone not found"},
    )


async def _cannot_create_on_lost_client_handler(
    request: Request, exc: CannotCreateOnLostClientError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "client_is_lost"},
    )


async def _lead_already_converted_handler(
    request: Request, exc: LeadAlreadyConvertedError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "already_converted",
            "client_id": str(exc.client_id) if exc.client_id is not None else None,
        },
    )


async def _lead_not_qualified_handler(
    request: Request, exc: LeadNotQualifiedError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "lead_not_qualified",
            "current_status": exc.current_status,
        },
    )


async def _rbac_forbidden_handler(request: Request, exc: RBACForbiddenError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden"},
    )


# ---------------------------------------------------------------------------
# Client-portal handlers (crm-client-portal slice)
# ---------------------------------------------------------------------------


async def _ticket_not_found_handler(request: Request, exc: TicketNotFoundError) -> JSONResponse:
    logger.info(
        "ticket_not_found",
        extra={"ticket_id": str(exc.ticket_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Ticket not found"},
    )


async def _message_not_found_handler(request: Request, exc: MessageNotFoundError) -> JSONResponse:
    logger.info(
        "message_not_found",
        extra={"message_id": str(exc.message_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Message not found"},
    )


# ---------------------------------------------------------------------------
# Billing-profile handlers (lead-role-billing-profiles slice)
# ---------------------------------------------------------------------------


async def _billing_profile_not_found_handler(
    request: Request, exc: BillingProfileNotFoundError
) -> JSONResponse:
    logger.info(
        "billing_profile_not_found",
        extra={"profile_id": str(exc.profile_id), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "Billing profile not found"},
    )


async def _duplicate_tax_id_handler(
    request: Request, exc: DuplicateTaxIdError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "duplicate_tax_id",
            "detail": f"A billing profile with tax_id '{exc.tax_id}' already exists for this client.",
        },
    )


async def _cannot_delete_only_default_handler(
    request: Request, exc: CannotDeleteOnlyDefaultError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "cannot_delete_only_default",
            "detail": "Cannot delete the only billing profile for this client.",
        },
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_domain_error_handlers(app: FastAPI) -> None:
    """Register domain exception → HTTP status handlers on the FastAPI app."""
    # Lead domain (existing)
    app.add_exception_handler(LeadNotFoundError, _lead_not_found_handler)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition_handler)
    app.add_exception_handler(RateLimitExceededError, _rate_limit_handler)

    # Client domain (crm-core-domain slice)
    app.add_exception_handler(ClientNotFoundError, _client_not_found_handler)
    app.add_exception_handler(ServiceNotFoundError, _service_not_found_handler)
    app.add_exception_handler(ContactNotFoundError, _contact_not_found_handler)
    app.add_exception_handler(MilestoneNotFoundError, _milestone_not_found_handler)
    app.add_exception_handler(CannotCreateOnLostClientError, _cannot_create_on_lost_client_handler)
    app.add_exception_handler(LeadAlreadyConvertedError, _lead_already_converted_handler)
    app.add_exception_handler(LeadNotQualifiedError, _lead_not_qualified_handler)
    app.add_exception_handler(RBACForbiddenError, _rbac_forbidden_handler)

    # Client-portal domain (crm-client-portal slice)
    app.add_exception_handler(TicketNotFoundError, _ticket_not_found_handler)
    app.add_exception_handler(MessageNotFoundError, _message_not_found_handler)

    # Billing-profile domain (lead-role-billing-profiles slice)
    app.add_exception_handler(BillingProfileNotFoundError, _billing_profile_not_found_handler)
    app.add_exception_handler(DuplicateTaxIdError, _duplicate_tax_id_handler)
    app.add_exception_handler(CannotDeleteOnlyDefaultError, _cannot_delete_only_default_handler)

    logger.info("Registered domain error handlers (Lead + Client domain + Client-portal + Billing)")
