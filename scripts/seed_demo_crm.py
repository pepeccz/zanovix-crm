"""
Idempotent seed script — populates the CRM core domain with demo data so the
admin panel and client portal render with real content.

Creates:
  - 6 demo clients spanning all 5 active pipeline stages plus one lost.
  - 1-2 contacts per client.
  - Active clients get 1-2 services (assessment / development / formation)
    with 3-5 milestones each (some completed, some pending).
  - One service flagged as type=assessment carries a diagnostic_json payload
    so the /client/diagnostic portal view has data.
  - Activity log entries for each significant event (stage_change,
    service_started, milestone_completed, contact_added, lead_converted).
  - One client_user account linked to the first active client, so the
    /client portal can be tested end-to-end with:
        demo.client@example.com  /  $SEED_CLIENT_USER_PASSWORD (default dev fallback)

Usage:
    docker compose exec api python -m scripts.seed_demo_crm

Idempotency: clients are identified by (name, sector). Re-running the script
upserts (skips existing client rows, but adds any missing children).

Owners default to the seeded users (admin@zanovix.com / consultor@zanovix.com /
comercial@zanovix.com). Run scripts.seed_users first.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone

from passlib.hash import bcrypt
from sqlalchemy import select

from database.connection import get_async_session
from database.models.activity_log import ActivityLog
from database.models.client import Client
from database.models.contact import Contact
from database.models.milestone import Milestone
from database.models.service import Service
from database.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_NOW = datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _NOW - timedelta(days=n)


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

CLIENTS = [
    {
        "name": "Clínica Dental Ramírez",
        "sector": "Salud",
        "size": "PYME",
        "region": "Málaga",
        "stage": "active",
        "mrr_cents": 280_000,
        "lifetime_value_cents": 850_000,
        "next_milestone": "Revisión trimestral de modelo",
        "entered_at": _days_ago(120),
        "owner_email": "consultor@zanovix.com",
        "contacts": [
            {"name": "Lucía Ramírez", "role": "CEO", "email": "lucia@clinicaramirez.es", "phone": "+34 612 000 001", "is_primary": True},
            {"name": "Pablo Mena", "role": "Director clínico", "email": "pablo@clinicaramirez.es", "phone": "+34 612 000 002", "is_primary": False},
        ],
        "services": [
            {
                "type": "assessment",
                "title": "AI Readiness Assessment 2026",
                "state": "completed",
                "progress_pct": 100,
                "setup_price_cents": 350_000,
                "monthly_cents": 0,
                "score": 78,
                "started_at": _days_ago(110),
                "ended_at": _days_ago(80),
                "milestones": [
                    {"title": "Kick-off + entrevistas", "due_offset": -100, "completed_offset": -98},
                    {"title": "Análisis de procesos", "due_offset": -90, "completed_offset": -88},
                    {"title": "Informe + sesión ejecutiva", "due_offset": -80, "completed_offset": -80},
                ],
                "diagnostic_json": {
                    "dimensions": {
                        "data": 82,
                        "processes": 75,
                        "team": 71,
                        "infrastructure": 80,
                        "compliance": 88,
                        "leadership": 72,
                    },
                    "summary": "La clínica tiene una base de datos clínica madura y procesos bien definidos; el techo está en formación del equipo y gobierno de IA.",
                    "plan": [
                        {"title": "Triaje automático de pacientes", "status": "go", "body": "Modelo de clasificación inicial sobre histórico anonimizado. ROI claro a 6 meses."},
                        {"title": "Predicción de no-show", "status": "go", "body": "Reduce huecos en agenda; integrable con el sistema actual."},
                        {"title": "Asistente clínico generativo", "status": "wait", "body": "Esperar a tener cumplimiento HIPAA-ES revisado."},
                        {"title": "Reconocimiento radiográfico", "status": "skip", "body": "Coste de despliegue supera el volumen de imágenes mensual."},
                    ],
                },
            },
            {
                "type": "development",
                "title": "Triaje IA fase 1",
                "state": "running",
                "progress_pct": 45,
                "setup_price_cents": 1_200_000,
                "monthly_cents": 280_000,
                "score": None,
                "started_at": _days_ago(45),
                "ended_at": None,
                "milestones": [
                    {"title": "Setup infraestructura", "due_offset": -35, "completed_offset": -30},
                    {"title": "MVP modelo base", "due_offset": -15, "completed_offset": -12},
                    {"title": "Integración con ficha clínica", "due_offset": 10, "completed_offset": None},
                    {"title": "Piloto en consulta", "due_offset": 30, "completed_offset": None},
                    {"title": "Validación clínica + handover", "due_offset": 60, "completed_offset": None},
                ],
            },
        ],
    },
    {
        "name": "Iberia Logística",
        "sector": "Logística",
        "size": "Mediana",
        "region": "Madrid",
        "stage": "active",
        "mrr_cents": 450_000,
        "lifetime_value_cents": 1_350_000,
        "next_milestone": "Demo modelo ETA",
        "entered_at": _days_ago(80),
        "owner_email": "admin@zanovix.com",
        "contacts": [
            {"name": "Marcos Ibáñez", "role": "COO", "email": "marcos@iberialog.es", "phone": "+34 611 200 010", "is_primary": True},
        ],
        "services": [
            {
                "type": "development",
                "title": "Predicción ETA flota",
                "state": "review",
                "progress_pct": 80,
                "setup_price_cents": 2_400_000,
                "monthly_cents": 450_000,
                "score": None,
                "started_at": _days_ago(70),
                "ended_at": None,
                "milestones": [
                    {"title": "Ingesta histórico GPS", "due_offset": -60, "completed_offset": -55},
                    {"title": "Modelo baseline", "due_offset": -45, "completed_offset": -40},
                    {"title": "Modelo + features clima", "due_offset": -20, "completed_offset": -18},
                    {"title": "Validación A/B en producción", "due_offset": 5, "completed_offset": None},
                ],
            },
        ],
    },
    {
        "name": "Café del Sur",
        "sector": "Hostelería",
        "size": "Micro",
        "region": "Sevilla",
        "stage": "proposal_sent",
        "mrr_cents": 0,
        "lifetime_value_cents": 0,
        "next_milestone": "Esperando respuesta a propuesta",
        "entered_at": _days_ago(15),
        "owner_email": "comercial@zanovix.com",
        "contacts": [
            {"name": "Andrea Soto", "role": "Fundadora", "email": "andrea@cafedelsur.com", "phone": "+34 619 030 040", "is_primary": True},
        ],
        "services": [],
    },
    {
        "name": "Bufete Aragón & Asociados",
        "sector": "Legal",
        "size": "Mediana",
        "region": "Zaragoza",
        "stage": "discovery_done",
        "mrr_cents": 0,
        "lifetime_value_cents": 0,
        "next_milestone": "Preparar propuesta",
        "entered_at": _days_ago(8),
        "owner_email": "consultor@zanovix.com",
        "contacts": [
            {"name": "Eva Aragón", "role": "Socia directora", "email": "eva@aragon-abogados.es", "phone": "+34 615 700 200", "is_primary": True},
            {"name": "David Trillo", "role": "IT lead", "email": "david@aragon-abogados.es", "phone": "+34 615 700 201", "is_primary": False},
        ],
        "services": [],
    },
    {
        "name": "AgroVeg Levante",
        "sector": "Agroalimentario",
        "size": "Grande",
        "region": "Valencia",
        "stage": "discovery_scheduled",
        "mrr_cents": 0,
        "lifetime_value_cents": 0,
        "next_milestone": "Discovery 18/05",
        "entered_at": _days_ago(3),
        "owner_email": "admin@zanovix.com",
        "contacts": [
            {"name": "Joan Esteve", "role": "CTO", "email": "joan@agroveg.es", "phone": "+34 622 410 410", "is_primary": True},
        ],
        "services": [],
    },
    {
        "name": "Nórdico Studio",
        "sector": "Diseño",
        "size": "Micro",
        "region": "Bilbao",
        "stage": "lost",
        "mrr_cents": 0,
        "lifetime_value_cents": 0,
        "next_milestone": None,
        "entered_at": _days_ago(60),
        "owner_email": "comercial@zanovix.com",
        "contacts": [
            {"name": "Iker Mendía", "role": "Fundador", "email": "iker@nordico.studio", "phone": "+34 688 900 900", "is_primary": True},
        ],
        "services": [],
    },
]


async def _resolve_owner(session, email: str | None) -> uuid.UUID | None:
    if not email:
        return None
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    return user.id if user else None


async def _seed_client_user_for(session, client: Client) -> None:
    """Create a demo client_user linked to the given client (idempotent)."""
    email = "demo.client@example.com"
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    raw_password = os.environ.get("SEED_CLIENT_USER_PASSWORD", "dev-changeme-client")
    if existing:
        if existing.client_id != client.id:
            existing.client_id = client.id
            logger.info("[seed-crm] link existing demo client_user -> %s", client.name)
        return
    user = User(
        id=uuid.uuid4(),
        email=email,
        display_name="Demo cliente · Ramírez",
        role="client_user",
        password_hash=bcrypt.hash(raw_password),
        is_active=True,
        client_id=client.id,
    )
    session.add(user)
    logger.info("[seed-crm] create client_user %s -> %s", email, client.name)


async def main() -> None:
    created_clients = 0
    skipped_clients = 0

    async with get_async_session() as session:
        first_active_client: Client | None = None

        for spec in CLIENTS:
            existing_q = await session.execute(
                select(Client).where(
                    Client.name == spec["name"],
                    Client.sector == spec["sector"],
                )
            )
            client = existing_q.scalar_one_or_none()

            if client is None:
                owner_id = await _resolve_owner(session, spec["owner_email"])
                client = Client(
                    id=uuid.uuid4(),
                    name=spec["name"],
                    sector=spec["sector"],
                    size=spec["size"],
                    region=spec["region"],
                    stage=spec["stage"],
                    mrr_cents=spec["mrr_cents"],
                    lifetime_value_cents=spec["lifetime_value_cents"],
                    entered_at=spec["entered_at"],
                    owner_id=owner_id,
                )
                session.add(client)
                await session.flush()
                created_clients += 1
                logger.info("[seed-crm] create client %s (stage=%s)", client.name, client.stage)

                # Initial stage_change activity
                session.add(
                    ActivityLog(
                        id=uuid.uuid4(),
                        client_id=client.id,
                        kind="stage_change",
                        actor_user_id=owner_id,
                        body=f"Cliente creado en etapa {client.stage}.",
                        created_at=spec["entered_at"],
                    )
                )
            else:
                skipped_clients += 1
                logger.info("[seed-crm] skip  client %s (exists)", client.name)

            # Contacts
            for c in spec["contacts"]:
                cq = await session.execute(
                    select(Contact).where(
                        Contact.client_id == client.id,
                        Contact.email == c["email"],
                    )
                )
                if cq.scalar_one_or_none() is not None:
                    continue
                session.add(
                    Contact(
                        id=uuid.uuid4(),
                        client_id=client.id,
                        name=c["name"],
                        role=c["role"],
                        email=c["email"],
                        phone=c["phone"],
                        is_primary=c["is_primary"],
                    )
                )
                session.add(
                    ActivityLog(
                        id=uuid.uuid4(),
                        client_id=client.id,
                        kind="contact_added",
                        actor_user_id=client.owner_id,
                        body=f"Contacto añadido: {c['name']} ({c['role']}).",
                        created_at=spec["entered_at"] + timedelta(hours=2),
                    )
                )

            # Services + milestones
            for svc in spec["services"]:
                sq = await session.execute(
                    select(Service).where(
                        Service.client_id == client.id,
                        Service.title == svc["title"],
                    )
                )
                service = sq.scalar_one_or_none()
                if service is None:
                    service = Service(
                        id=uuid.uuid4(),
                        client_id=client.id,
                        owner_id=client.owner_id,
                        type=svc["type"],
                        title=svc["title"],
                        state=svc["state"],
                        progress_pct=svc["progress_pct"],
                        setup_price_cents=svc["setup_price_cents"],
                        monthly_cents=svc["monthly_cents"],
                        score_int=svc["score"],
                        started_at=svc["started_at"],
                        ended_at=svc["ended_at"],
                        diagnostic_json=svc.get("diagnostic_json"),
                    )
                    session.add(service)
                    await session.flush()
                    session.add(
                        ActivityLog(
                            id=uuid.uuid4(),
                            client_id=client.id,
                            kind="service_started",
                            actor_user_id=client.owner_id,
                            body=f"Servicio iniciado: {service.title}.",
                            created_at=svc["started_at"],
                        )
                    )

                for n, ms in enumerate(svc["milestones"], start=1):
                    mq = await session.execute(
                        select(Milestone).where(
                            Milestone.service_id == service.id,
                            Milestone.n == n,
                        )
                    )
                    if mq.scalar_one_or_none() is not None:
                        continue
                    due_date = date.today() + timedelta(days=ms["due_offset"])
                    completed_at = (
                        _days_ago(-ms["completed_offset"])
                        if ms["completed_offset"] is not None
                        else None
                    )
                    session.add(
                        Milestone(
                            id=uuid.uuid4(),
                            service_id=service.id,
                            n=n,
                            title=ms["title"],
                            due_date=due_date,
                            completed_at=completed_at,
                        )
                    )
                    if completed_at is not None:
                        session.add(
                            ActivityLog(
                                id=uuid.uuid4(),
                                client_id=client.id,
                                kind="milestone_completed",
                                actor_user_id=client.owner_id,
                                body=f"Hito completado: {ms['title']}.",
                                created_at=completed_at,
                            )
                        )

            if client.stage == "active" and first_active_client is None:
                first_active_client = client

        # Wire the demo client_user to the first active client we saw.
        if first_active_client is not None:
            await _seed_client_user_for(session, first_active_client)

        await session.commit()

    print(
        f"[seed-crm] created {created_clients} clients, skipped {skipped_clients}. "
        "demo.client@example.com is the portal test user."
    )


if __name__ == "__main__":
    asyncio.run(main())
