"""
Integration test fixtures for the CRM API.

Strategy:
- Use httpx.AsyncClient with ASGITransport to call the real FastAPI app in-process.
- Override get_current_user via app.dependency_overrides. Because require_role()
  closures call Depends(get_current_user) internally, overriding get_current_user
  is sufficient — role checks work naturally against the injected user's role.
- Real PostgreSQL DB is used (same instance as the app). Rows are deleted between
  tests via an autouse fixture so each test starts with a clean slate.
- Users are created once per session and reused across all tests in a session.

Environment:
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

from api.auth import get_current_user
from api.main import app
from database.models import ActivityLog, Client, Contact, Milestone, Service
from database.models.user import User
from shared.config import get_settings

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


# ---------------------------------------------------------------------------
# Autouse cleanup — delete all CRM rows between tests (NOT users)
# ---------------------------------------------------------------------------


async def _delete_crm_rows(session_factory) -> None:
    """Delete all CRM aggregate rows. FK-safe order: children before parents."""
    async with session_factory() as session:
        await session.execute(delete(ActivityLog))
        await session.execute(delete(Milestone))
        await session.execute(delete(Contact))
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
# Role-specific AsyncClient fixtures
# ---------------------------------------------------------------------------
#
# We override get_current_user in app.dependency_overrides.
# require_role() closures use Depends(get_current_user) internally, so they
# automatically receive our injected user and check their role against it.
# No monkey-patching needed.


def _make_user_override(user: User):
    """Build a zero-arg dependency that always returns `user`."""

    async def _override() -> User:
        return user

    return _override


@pytest.fixture
async def admin_client(admin_user: User) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient that authenticates all requests as the admin user."""
    app.dependency_overrides[get_current_user] = _make_user_override(admin_user)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def comercial_client(
    comercial_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as comercial."""
    app.dependency_overrides[get_current_user] = _make_user_override(comercial_user)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def consultor_client(
    consultor_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as consultor."""
    app.dependency_overrides[get_current_user] = _make_user_override(consultor_user)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def consultor_b_client(
    consultor_b_user: User,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient authenticated as a second consultor (consultor_b)."""
    app.dependency_overrides[get_current_user] = _make_user_override(consultor_b_user)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


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
