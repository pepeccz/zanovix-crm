"""
Idempotent seed script — creates 5 demo leads with mixed verticals, channels,
and statuses.

Usage:
    python -m scripts.seed_demo_leads
    python scripts/seed_demo_leads.py

Idempotency: each lead is identified by the (email, channel, vertical) tuple.
If a row with the same combination already exists it is skipped.

Owner lookup: owner users are resolved by email from the users table.
If a user is not found, owner_id is set to NULL and a WARNING is logged.
Run seed_users first.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select

from database.connection import get_async_session
from database.models.lead import Lead
from database.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raw_payload() -> dict:
    return {
        "headers": {"User-Agent": "seed-script"},
        "body": {"source": "seed"},
        "ingested_at": _now_iso(),
    }


# Seed definition — (email, channel, vertical) must be unique per record.
# owner_email=None means owner_id=NULL.
LEADS_TO_SEED = [
    {
        "name": "Clínica Dental Ramírez",
        "email": "clinica.ramirez@example.com",
        "phone": "+34 612 000 001",
        "company": "Clínica Dental Ramírez SL",
        "vertical": "clinicas_dentales",
        "channel": "email_marketing",
        "status": "new",
        "notes": "Lead captado por campaña de email Q1.",
        "owner_email": None,
    },
    {
        "name": "Dra. Laura Vega",
        "email": "laura.vega@odontologia.es",
        "phone": "+34 612 000 002",
        "company": "Clínica Vega Dental",
        "vertical": "clinicas_dentales",
        "channel": "cold_calling",
        "status": "contacted",
        "notes": "Primer contacto realizado. Pendiente demo.",
        "owner_email": "consultor@zanovix.com",
    },
    {
        "name": "Carlos Montes",
        "email": "carlos.montes@empresa.com",
        "phone": "+34 612 000 003",
        "company": "Montes & Asociados",
        "vertical": "general",
        "channel": "networking",
        "status": "qualified",
        "notes": "Conocido en evento Madrid Tech 2026. Alta intención de compra.",
        "owner_email": "consultor@zanovix.com",
    },
    {
        "name": "Clínica Oral Beltran",
        "email": "info@clinicabeltran.es",
        "phone": "+34 612 000 004",
        "company": "Clínica Oral Beltran",
        "vertical": "clinicas_dentales",
        "channel": "referral",
        "status": "converted",
        "notes": "Referido por cliente existente. Contrato firmado.",
        "owner_email": "comercial@zanovix.com",
    },
    {
        "name": "Sara Lozano",
        "email": "sara.lozano@gmail.com",
        "phone": None,
        "company": None,
        "vertical": "general",
        "channel": "web_form",
        "status": "disqualified",
        "notes": "No perfil de cliente. Descartado.",
        "owner_email": None,
    },
]


async def _resolve_owner(
    session, owner_email: str | None
) -> uuid.UUID | None:
    if owner_email is None:
        return None
    result = await session.execute(
        select(User).where(User.email == owner_email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(
            "[seed] owner user %s not found — setting owner_id=NULL. "
            "Run seed_users first.",
            owner_email,
        )
        return None
    return user.id


async def main() -> None:
    created = 0
    skipped = 0

    async with get_async_session() as session:
        for spec in LEADS_TO_SEED:
            # Idempotency check: (email, channel, vertical) tuple
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.email == spec["email"],
                        Lead.channel == spec["channel"],
                        Lead.vertical == spec["vertical"],
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                logger.info(
                    "[seed] skip  %s / %s / %s (already exists)",
                    spec["email"],
                    spec["channel"],
                    spec["vertical"],
                )
                skipped += 1
                continue

            owner_id = await _resolve_owner(session, spec["owner_email"])

            lead = Lead(
                id=uuid.uuid4(),
                name=spec["name"],
                email=spec["email"],
                phone=spec.get("phone"),
                company=spec.get("company"),
                vertical=spec["vertical"],
                channel=spec["channel"],
                status=spec["status"],
                notes=spec.get("notes"),
                owner_id=owner_id,
                raw_payload=_raw_payload(),
            )
            session.add(lead)
            logger.info(
                "[seed] create %s (vertical=%s channel=%s status=%s)",
                spec["email"],
                spec["vertical"],
                spec["channel"],
                spec["status"],
            )
            created += 1

        await session.commit()

    print(f"[seed] created {created} leads, skipped {skipped} (already exist)")


if __name__ == "__main__":
    asyncio.run(main())
