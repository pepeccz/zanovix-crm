"""
Zanovix CRM — FastAPI entry point.

Bootstrap: CORS, structured logging, error handlers, router includes.
MSI-a domain routes (chatwoot, tariffs, cases, elements, billing) have been removed.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.errors import register_domain_error_handlers
from api.routes import admin
from api.routes import activity, clients, contacts, leads, me, messages, milestones, services, tickets
from api.routes.billing_profiles import flat_router as billing_flat_router, nested_router as billing_nested_router
from shared.config import get_settings
from shared.logging_config import configure_logging
from shared.fastapi_errors import register_error_handlers

# Configure structured JSON logging on startup
configure_logging()
logger = logging.getLogger(__name__)


def build_app() -> FastAPI:
    """
    Construct and return a fully configured FastAPI application instance.

    Extracted from module-level so that integration tests can create isolated
    instances (one per role-scoped fixture) without sharing mutable state such
    as ``dependency_overrides``.  The uvicorn-loaded singleton ``app`` below
    calls this function exactly once at import time — no behaviour change for
    production.
    """
    settings = get_settings()

    _app = FastAPI(
        title="Zanovix CRM API",
        description="Lead capture and management API",
        version="0.1.0",
    )

    # CORS
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )

    # Error handlers (generic HTTP + validation)
    register_error_handlers(_app)
    # Domain error handlers (Lead aggregate)
    register_domain_error_handlers(_app)

    # Routers
    _app.include_router(admin.router)
    _app.include_router(activity.router, prefix="/api")
    _app.include_router(leads.router, prefix="/api")
    _app.include_router(clients.router, prefix="/api")
    _app.include_router(contacts.router, prefix="/api")
    _app.include_router(services.router, prefix="/api")
    _app.include_router(milestones.router, prefix="/api")
    _app.include_router(billing_nested_router, prefix="/api")
    _app.include_router(billing_flat_router, prefix="/api")

    # Client-portal routes — gated by CLIENT_PORTAL_ENABLED env flag (design §Migration/Rollout)
    if settings.CLIENT_PORTAL_ENABLED:
        _app.include_router(me.router, prefix="/api")
        # Internal extensions: messages + tickets under /api/clients/{id}/* and /api/tickets/*
        _app.include_router(messages.router, prefix="/api")
        _app.include_router(tickets.router, prefix="/api")
        logger.info("client_portal_routes_mounted", extra={"prefix": "/api/me"})
    else:
        logger.info("client_portal_routes_disabled", extra={"reason": "CLIENT_PORTAL_ENABLED=false"})

    return _app


# Singleton consumed by uvicorn and by any import that does ``from api.main import app``.
# Tests MUST NOT mutate this instance's dependency_overrides — use make_role_app() instead.
app = build_app()


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check — verifies Redis and PostgreSQL connectivity."""
    from sqlalchemy import text
    from database.connection import get_async_session
    from shared.redis_client import get_redis_client

    health_status = {
        "status": "healthy",
        "service": get_settings().PROJECT_NAME,
        "redis": "unknown",
        "postgres": "unknown",
    }
    status_code = 200

    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["redis"] = "connected"
    except Exception:
        health_status["redis"] = "disconnected"
        health_status["status"] = "degraded"
        status_code = 503

    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["postgres"] = "connected"
    except Exception:
        health_status["postgres"] = "disconnected"
        health_status["status"] = "degraded"
        status_code = 503

    return JSONResponse(status_code=status_code, content=health_status)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": "0.1.0",
        "health": "/health",
    }
