"""
Integration test fixtures for the CRM API.

Strategy
--------
- Use httpx.AsyncClient with ASGITransport to call the real FastAPI app in-process.
- Each role-scoped client fixture builds its OWN FastAPI app instance via
  ``make_role_app(user)`` (see ``_app_factory.py``).  The ``get_current_user``
  dependency is overridden at construction time on that isolated instance, so
  concurrent fixtures can never clobber each other's overrides (W01 fix).
- Real PostgreSQL DB is used (same instance as the app). Rows are deleted between
  tests via an autouse fixture so each test starts with a clean slate.
- Users are created once per session and reused across all tests in a session.

W01 fix (conftest dependency-override race)
-------------------------------------------
Previously, all client fixtures mutated ``app.dependency_overrides`` on the shared
singleton.  When a test requested both ``admin_client`` and ``consultor_client`` the
second fixture's ``set`` would overwrite the first, making RBAC assertions unreliable.
The factory approach gives each fixture its own ``FastAPI`` instance with its own
``dependency_overrides`` dict.  No cleanup of overrides is needed — the app is
garbage-collected after the fixture scope ends.

Environment
-----------
- Requires DATABASE_URL to point at an accessible PostgreSQL instance.
  Default (docker-compose): postgresql+asyncpg://zanovix:changeme@localhost:5433/zanovix_crm
  Override via DATABASE_URL environment variable before running pytest.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.auth import get_current_user  # noqa: F401 — kept for backward compat imports
from database.models import ActivityLog, Client, Contact, Message, Milestone, Service, Ticket
from database.models.user import User
from shared.config import get_settings
from tests.integration._app_factory import make_role_app

settings = get_settings()


# ---------------------------------------------------------------------------
# Session-scoped DB engine + session factory
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def test_engine():
    """Async engine for the test session. Reuses the app DATABASE_URL."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Async session factory backed by test_engine."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# ---------------------------------------------------------------------------
# User fixtures (session-scoped — created once, reused)
# ---------------------------------------------------------------------------


async def _ensure_user(
    session_factory,
    email: str,
    role: str,
    display_name: str,
) -> User:
    """
    Create a User if it doesn't already exist and return the ORM object.
    Tests never hash passwords — a placeholder string is stored.
    """
    from sqlalchemy import select as sa_select

    async with session_factory() as session:
        stmt = sa_select(User).where(User.email == email)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="$2b$12$test_placeholder_not_a_real_hash",
            role=role,
            display_name=display_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture(scope="session")
async def admin_user(test_session_factory) -> User:
    return await _ensure_user(
        test_session_factory,
        email="admin.test@zanovix.test",
        role="admin",
        display_name="Test Admin",
    )


@pytest.fixture(scope="session")
async def comercial_user(test_session_factory) -> User:
    return await _ensure_user(
        test_session_factory,
        email="comercial.test@zanovix.test",
        role="comercial",
        display_name="Test Comercial",
    )


@pytest.fixture(scope="session")
async def consultor_user(test_session_factory) -> User:
    return await _ensure_user(
        test_session_factory,
        email="consultor.test@zanovix.test",
        role="consultor",
        display_name="Test Consultor",
    )


@pytest.fixture(scope="session")
async def consultor_b_user(test_session_factory) -> User:
    """Second consultor — used to test cross-owner RBAC isolation."""
    return await _ensure_user(
        test_session_factory,
        email="consultor.b.test@zanovix.test",
        role="consultor",
        display_name="Test Consultor B",
    )


@pytest.fixture(scope="session")
async def client_user(test_session_factory) -> User:
    """
    A real client_user row persisted in the DB (session-scoped).

    client_id is set to None at creation time; ``test_client_for_portal``
    updates it to a valid Client.id before each test so FK constraints are
    always satisfied.
    """
    from sqlalchemy import select as sa_select

    email = "client.portal.test@zanovix.test"
    async with test_session_factory() as session:
        stmt = sa_select(User).where(User.email == email)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="$2b$12$test_placeholder_not_a_real_hash",
            role="client_user",
            display_name="Test Client Portal User",
            is_active=True,
            client_id=None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def test_client_for_portal(
    test_session_factory,
    client_user: User,
    cleanup_crm_rows,  # explicit dep ensures this runs AFTER pre-test cleanup
) -> "Client":
    """
    A real Client row seeded fresh for each test (function-scoped).

    Because ``cleanup_crm_rows`` deletes ALL Client rows between tests, this
    fixture re-creates the portal client AFTER cleanup has run (it depends on
    ``cleanup_crm_rows`` indirectly via test ordering).  It also updates
    ``client_user.client_id`` to point at the new row so the FK is always
    valid for the lifetime of the test.
    """
    from sqlalchemy import select as sa_select, update as sa_update

    async with test_session_factory() as session:
        portal_client = Client(
            id=uuid.uuid4(),
            name="Portal Test Client",
            stage="active",
        )
        session.add(portal_client)
        await session.flush()

        # Keep client_user.client_id in sync so ticket/message FKs are valid.
        await session.execute(
            sa_update(User)
            .where(User.id == client_user.id)
            .values(client_id=portal_client.id)
        )
        await session.commit()
        await session.refresh(portal_client)

        # Update the in-memory User object so callers see the new client_id.
        client_user.client_id = portal_client.id

        return portal_client


# ---------------------------------------------------------------------------
# Autouse cleanup — delete all CRM rows between tests (NOT users)
# ---------------------------------------------------------------------------


async def _delete_crm_rows(session_factory) -> None:
    """Delete all CRM aggregate rows. FK-safe order: children before parents."""
    async with session_factory() as session:
        await session.execute(delete(ActivityLog))
        await session.execute(delete(Milestone))
        await session.execute(delete(Contact))
        await session.execute(delete(Message))
        await session.execute(delete(Ticket))
        await session.execute(delete(Service))
        await session.execute(text("DELETE FROM leads"))
        await session.execute(delete(Client))
        await session.commit()


@pytest.fixture(autouse=True)
async def cleanup_crm_rows(test_session_factory) -> AsyncGenerator[None, None]:
    """
    Delete all CRM aggregate rows before AND after each test so each test starts
    and ends with a clean state. Users are preserved (session-scoped fixtures).

    Pre-test cleanup handles leftover data from a previous failed session.
    Post-test cleanup is the primary isolation mechanism between tests.
    """
    await _delete_crm_rows(test_session_factory)
    yield
    await _delete_crm_rows(test_session_factory)


# ---------------------------------------------------------------------------
# Role-specific AsyncClient fixtures  (W01 fix — isolated app per role)
# ---------------------------------------------------------------------------
#
# Each fixture builds its own FastAPI app via make_role_app(user).
# The get_current_user override is set on that isolated instance only, so
# concurrent fixtures never share or clobber each other's overrides.
# No cleanup of dependency_overrides is needed — the app is GC'd when the
# fixture scope ends.


@pytest.fixture
async def admin_client(admin_user: User) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient that authenticates all requests as the admin user."""
    role_app = make_role_app(admin_user)
    transport = httpx.ASGITransport(app=role_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def comercial_client(
    comercial_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as comercial."""
    role_app = make_role_app(comercial_user)
    transport = httpx.ASGITransport(app=role_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def consultor_client(
    consultor_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as consultor."""
    role_app = make_role_app(consultor_user)
    transport = httpx.ASGITransport(app=role_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def consultor_b_client(
    consultor_b_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as a second consultor (consultor_b)."""
    role_app = make_role_app(consultor_b_user)
    transport = httpx.ASGITransport(app=role_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Payload factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_client_payload():
    """Factory for valid ClientCreate payload dicts."""

    def _factory(
        name: str = "ACME Corp",
        sector: str | None = "tech",
        stage: str = "lead",
        owner_id: uuid.UUID | None = None,
    ) -> dict:
        payload: dict = {"name": name, "sector": sector, "stage": stage}
        if owner_id is not None:
            payload["owner_id"] = str(owner_id)
        return payload

    return _factory


@pytest.fixture
def make_service_payload():
    """Factory for valid ServiceCreate payload dicts."""

    def _factory(
        client_id: str | None = None,
        type: str = "assessment",
        title: str = "AI Assessment Q1",
        owner_id: uuid.UUID | None = None,
    ) -> dict:
        payload: dict = {
            "type": type,
            "title": title,
            "client_id": client_id or str(uuid.uuid4()),
        }
        if owner_id is not None:
            payload["owner_id"] = str(owner_id)
        return payload

    return _factory
