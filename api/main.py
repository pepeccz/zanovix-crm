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
from api.routes import clients, contacts, leads, milestones, services
from shared.config import get_settings
from shared.logging_config import configure_logging
from shared.fastapi_errors import register_error_handlers

# Configure structured JSON logging on startup
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Zanovix CRM API",
    description="Lead capture and management API",
    version="0.1.0",
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Error handlers (generic HTTP + validation)
register_error_handlers(app)
# Domain error handlers (Lead aggregate)
register_domain_error_handlers(app)

# Routers
app.include_router(admin.router)
app.include_router(leads.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(milestones.router, prefix="/api")


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check — verifies Redis and PostgreSQL connectivity."""
    from sqlalchemy import text
    from database.connection import get_async_session
    from shared.redis_client import get_redis_client

    health_status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
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
