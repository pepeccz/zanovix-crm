"""
Diagnostic service — read-only access to services.diagnostic_json.

Design principles (design §D6):
- diagnostic_json is a JSONB column on the services table.
- Only meaningful when services.type == 'assessment'.
- Admin writes raw JSONB directly; no write endpoint in this slice.
- Returns a parsed DiagnosticRead when data is present, or None.
- services flush; routes commit (read-only — no flush needed here).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.diagnostic import DiagnosticRead
from api.services.exceptions import ServiceNotFoundError
from database.models.service import Service

logger = logging.getLogger(__name__)


class DiagnosticService:
    """
    Read-only service for the assessment diagnostic resource.

    Instantiated per-request with an AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_diagnostic(
        self,
        service_id: uuid.UUID,
        *,
        client_id_filter: uuid.UUID | None,
    ) -> DiagnosticRead | None:
        """
        Return the parsed diagnostic for a service, or None if not available.

        Returns None (not an error) when:
        - service.diagnostic_json IS NULL
        - service.type != 'assessment'

        Raises:
            ServiceNotFoundError: service not found or outside caller's client scope.
        """
        stmt = select(Service).where(Service.id == service_id)
        if client_id_filter is not None:
            stmt = stmt.where(Service.client_id == client_id_filter)

        service = (await self.session.execute(stmt)).scalar_one_or_none()
        if service is None:
            raise ServiceNotFoundError(service_id)

        # Diagnostic only meaningful for assessment type
        if service.type != "assessment" or service.diagnostic_json is None:
            return None

        try:
            return DiagnosticRead.model_validate(service.diagnostic_json)
        except Exception:
            logger.warning(
                "diagnostic_json_parse_failed",
                extra={"service_id": str(service_id)},
            )
            return None
