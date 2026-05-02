"""
Domain exception → HTTP response mapping.

Registers FastAPI exception handlers for domain-level exceptions raised by
the service layer. These handlers live here (not in shared/) because they are
specific to this application's domain model.

Handlers registered:
  LeadNotFoundError          → 404
  InvalidTransitionError     → 409 with allowed_transitions in body
  RateLimitExceededError     → 429 (fallback; normally HTTPException(429) raised directly)

Usage:
    from api.errors import register_domain_error_handlers
    register_domain_error_handlers(app)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.services.exceptions import (
    InvalidTransitionError,
    LeadNotFoundError,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)


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


def register_domain_error_handlers(app: FastAPI) -> None:
    """Register domain exception → HTTP status handlers on the FastAPI app."""
    app.add_exception_handler(LeadNotFoundError, _lead_not_found_handler)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition_handler)
    app.add_exception_handler(RateLimitExceededError, _rate_limit_handler)
    logger.info("Registered domain error handlers (Lead domain)")
