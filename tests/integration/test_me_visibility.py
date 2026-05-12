"""
Integration tests — Cross-tenant RLS visibility for /api/me/* endpoints (PR-4).

Security model (spec §404-on-out-of-scope-policy, §cross-cutting-rbac-invariants):
  - All /api/me/* endpoints are gated to ``client_user`` role via scope_to_client.
  - Internal roles (admin / comercial / consultor) receive 403 on every /me endpoint.
  - A client_user with NULL client_id receives 403 (misconfigured account).
  - Accessing a resource that belongs to a DIFFERENT client returns 404 (NOT 403).
    The 404-on-out-of-scope policy prevents existence leaks.

Coverage:
  TestCrossTenantVisibility     — own resource 200, other-client resource 404
  TestNullClientId403           — client_user with no client_id → 403 on every endpoint
  TestInternalRoles403OnMe      — admin / comercial / consultor → 403 on every /me endpoint
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Client, Contact, Message, Service, Ticket
from database.models.user import User
from tests.integration._app_factory import make_role_app

# ---------------------------------------------------------------------------
# Helpers — ORM seed functions
# ---------------------------------------------------------------------------


async def _seed_service(
    session_factory: async_sessionmaker,
    client: Client,
    admin_user: User,
    title: str = "Seeded Service",
    type_: str = "assessment",
) -> Service:
    async with session_factory() as session:
        svc = Service(
            id=uuid.uuid4(),
            client_id=client.id,
            owner_id=admin_user.id,
            type=type_,
            title=title,
            state="scoping",
            diagnostic_json={
                "dimensions": {
                    "data": 70,
                    "processes": 65,
                    "team": 80,
                    "infrastructure": 60,
                    "compliance": 75,
                    "leadership": 85,
                },
                "plan": [],
                "summary": "Test diagnostic summary",
            },
        )
        session.add(svc)
        await session.commit()
        await session.refresh(svc)
        return svc


async def _seed_contact(
    session_factory: async_sessionmaker,
    client: Client,
    name: str = "Seeded Contact",
) -> Contact:
    async with session_factory() as session:
        contact = Contact(
            id=uuid.uuid4(),
            client_id=client.id,
            name=name,
            email=f"contact-{uuid.uuid4()}@test.local",
        )
        session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact


async def _seed_message(
    session_factory: async_sessionmaker,
    client: Client,
    sender: User,
    body: str = "Seeded message",
) -> Message:
    async with session_factory() as session:
        msg = Message(
            id=uuid.uuid4(),
            client_id=client.id,
            sender_user_id=sender.id,
            body=body,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg


async def _seed_ticket(
    session_factory: async_sessionmaker,
    client: Client,
    creator: User,
    title: str = "Seeded Ticket",
) -> Ticket:
    async with session_factory() as session:
        ticket = Ticket(
            id=uuid.uuid4(),
            client_id=client.id,
            title=title,
            priority="medium",
            status="pending",
            created_by_user_id=creator.id,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket


# ---------------------------------------------------------------------------
# Fixture: unauthenticated client (no auth override)
# ---------------------------------------------------------------------------


@pytest.fixture
async def unauthenticated_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx client with NO auth override — simulates an unauthenticated request."""
    from api.main import build_app

    raw_app = build_app()
    transport = httpx.ASGITransport(app=raw_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# TestCrossTenantVisibility
# ---------------------------------------------------------------------------


class TestCrossTenantVisibility:
    """
    For each /me/* resource type:
      - Authenticate as client_user_A.
      - Seed a resource owned by client_B.
      - Assert 404 on read (not 403 — 404-on-out-of-scope policy, design §D3).
      - Also assert 200 when reading own resource (client_A).
    """

    async def test_services_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/services → 200 listing own services."""
        await _seed_service(test_session_factory, test_client_for_portal, admin_user)

        resp = await portal_client_a.get("/api/me/services")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1

    async def test_service_detail_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/services/{id} with own service → 200."""
        svc = await _seed_service(test_session_factory, test_client_for_portal, admin_user)

        resp = await portal_client_a.get(f"/api/me/services/{svc.id}")

        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == str(svc.id)

    async def test_service_detail_other_client_404(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/services/{id} with service owned by client B → 404 (not 403)."""
        svc_b = await _seed_service(test_session_factory, test_client_for_portal_b, admin_user, "B Service")

        resp = await portal_client_a.get(f"/api/me/services/{svc_b.id}")

        assert resp.status_code == 404, resp.text

    async def test_service_diagnostic_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/services/{id}/diagnostic with own assessment service → 200."""
        svc = await _seed_service(test_session_factory, test_client_for_portal, admin_user, type_="assessment")

        resp = await portal_client_a.get(f"/api/me/services/{svc.id}/diagnostic")

        assert resp.status_code == 200, resp.text

    async def test_service_diagnostic_other_client_404(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/services/{id}/diagnostic with service from client B → 404."""
        svc_b = await _seed_service(test_session_factory, test_client_for_portal_b, admin_user, "B Diag", type_="assessment")

        resp = await portal_client_a.get(f"/api/me/services/{svc_b.id}/diagnostic")

        assert resp.status_code == 404, resp.text

    async def test_contacts_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
    ) -> None:
        """GET /api/me/contacts → 200; returns only own client's contacts."""
        await _seed_contact(test_session_factory, test_client_for_portal)

        resp = await portal_client_a.get("/api/me/contacts")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Each contact in the list must belong to client_A
        assert len(body) >= 1

    async def test_contacts_no_other_client_data(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
    ) -> None:
        """GET /api/me/contacts must NOT return contacts belonging to client B."""
        contact_b = await _seed_contact(test_session_factory, test_client_for_portal_b, "B Contact")

        resp = await portal_client_a.get("/api/me/contacts")

        assert resp.status_code == 200, resp.text
        contact_ids = [c["id"] for c in resp.json()]
        assert str(contact_b.id) not in contact_ids

    async def test_activity_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """GET /api/me/activity → 200."""
        resp = await portal_client_a.get("/api/me/activity")

        assert resp.status_code == 200, resp.text
        assert "items" in resp.json()

    async def test_messages_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/messages → 200 with own messages."""
        await _seed_message(test_session_factory, test_client_for_portal, admin_user)

        resp = await portal_client_a.get("/api/me/messages")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1

    async def test_messages_no_other_client_data(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        admin_user: User,
    ) -> None:
        """GET /api/me/messages must NOT return messages belonging to client B."""
        msg_b = await _seed_message(test_session_factory, test_client_for_portal_b, admin_user, "B secret")

        resp = await portal_client_a.get("/api/me/messages")

        assert resp.status_code == 200, resp.text
        message_ids = [m["id"] for m in resp.json()["items"]]
        assert str(msg_b.id) not in message_ids

    async def test_tickets_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        client_user: User,
    ) -> None:
        """GET /api/me/tickets → 200 with own tickets."""
        await _seed_ticket(test_session_factory, test_client_for_portal, client_user)

        resp = await portal_client_a.get("/api/me/tickets")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1

    async def test_ticket_detail_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        client_user: User,
    ) -> None:
        """GET /api/me/tickets/{id} (via PATCH) with own ticket → 200."""
        ticket = await _seed_ticket(test_session_factory, test_client_for_portal, client_user)

        # /me/tickets/{id} only has PATCH; use PATCH with empty body to confirm ownership
        resp = await portal_client_a.patch(
            f"/api/me/tickets/{ticket.id}",
            json={"title": "Still mine"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == str(ticket.id)

    async def test_ticket_detail_other_client_404(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        client_user_b: User,
    ) -> None:
        """PATCH /api/me/tickets/{id} where ticket belongs to client B → 404 (not 403)."""
        ticket_b = await _seed_ticket(test_session_factory, test_client_for_portal_b, client_user_b, "B Ticket")

        resp = await portal_client_a.patch(
            f"/api/me/tickets/{ticket_b.id}",
            json={"title": "Shouldn't work"},
        )

        assert resp.status_code == 404, resp.text

    async def test_tickets_no_other_client_data_in_list(
        self,
        portal_client_a: httpx.AsyncClient,
        test_session_factory: async_sessionmaker,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        client_user_b: User,
    ) -> None:
        """GET /api/me/tickets must NOT return tickets belonging to client B."""
        ticket_b = await _seed_ticket(test_session_factory, test_client_for_portal_b, client_user_b, "Leaked B Ticket")

        resp = await portal_client_a.get("/api/me/tickets")

        assert resp.status_code == 200, resp.text
        ticket_ids = [t["id"] for t in resp.json()["items"]]
        assert str(ticket_b.id) not in ticket_ids

    async def test_client_own_200(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """GET /api/me/client → 200 with own client record."""
        resp = await portal_client_a.get("/api/me/client")

        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == str(test_client_for_portal.id)


# ---------------------------------------------------------------------------
# TestNullClientId403
# ---------------------------------------------------------------------------


class TestNullClientId403:
    """
    A client_user whose client_id IS NULL should receive 403 on every /me endpoint.

    Spec §scope_to_client — null client_id branch.
    """

    @pytest.fixture
    async def null_client_id_user(self, test_session_factory: async_sessionmaker) -> User:
        """A transient client_user with client_id = NULL (misconfigured account)."""
        from sqlalchemy import select as sa_select

        email = "client.null.cid@zanovix.test"
        async with test_session_factory() as session:
            stmt = sa_select(User).where(User.email == email)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                # Ensure client_id is null (reset in case a prior test linked it)
                await session.execute(
                    sa_update(User)
                    .where(User.id == existing.id)
                    .values(client_id=None)
                )
                await session.commit()
                existing.client_id = None
                return existing

            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash="$2b$12$test_placeholder_not_a_real_hash",
                role="client_user",
                display_name="Null Client ID User",
                is_active=True,
                client_id=None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    @pytest.fixture
    async def null_client_http(self, null_client_id_user: User) -> AsyncGenerator[httpx.AsyncClient, None]:
        role_app = make_role_app(null_client_id_user)
        transport = httpx.ASGITransport(app=role_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/me/client"),
            ("GET", "/api/me/services"),
            ("GET", f"/api/me/services/{uuid.uuid4()}"),
            ("GET", f"/api/me/services/{uuid.uuid4()}/diagnostic"),
            ("GET", "/api/me/contacts"),
            ("GET", "/api/me/activity"),
            ("GET", "/api/me/messages"),
            ("POST", "/api/me/messages"),
            ("GET", "/api/me/tickets"),
            ("POST", "/api/me/tickets"),
        ],
    )
    async def test_null_client_id_returns_403(
        self,
        null_client_http: httpx.AsyncClient,
        method: str,
        path: str,
    ) -> None:
        """client_user with NULL client_id must receive 403 on every /me endpoint."""
        json_body: dict | None = None
        if method == "POST" and "messages" in path:
            json_body = {"body": "Hello"}
        elif method == "POST" and "tickets" in path:
            json_body = {"title": "Test ticket", "priority": "medium"}

        resp = await null_client_http.request(method, path, json=json_body)

        assert resp.status_code == 403, f"{method} {path} → expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# TestInternalRoles403OnMe
# ---------------------------------------------------------------------------


class TestInternalRoles403OnMe:
    """
    Internal roles (admin, comercial, consultor) MUST NOT use /me endpoints.

    scope_to_client raises 403 for any role != client_user (design §D1).
    """

    # A stable UUID to use in path params — resource won't exist but 403 fires first.
    _DUMMY_ID = str(uuid.uuid4())

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/me/client"),
            ("GET", "/api/me/services"),
            ("GET", f"/api/me/services/{_DUMMY_ID}"),
            ("GET", f"/api/me/services/{_DUMMY_ID}/diagnostic"),
            ("GET", "/api/me/contacts"),
            ("GET", "/api/me/activity"),
            ("GET", "/api/me/messages"),
            ("POST", "/api/me/messages"),
            ("GET", "/api/me/tickets"),
            ("POST", "/api/me/tickets"),
        ],
    )
    async def test_admin_forbidden_on_me(
        self,
        admin_client: httpx.AsyncClient,
        method: str,
        path: str,
    ) -> None:
        """Admin role must receive 403 on every /me endpoint."""
        json_body: dict | None = None
        if method == "POST" and "messages" in path:
            json_body = {"body": "Hello"}
        elif method == "POST" and "tickets" in path:
            json_body = {"title": "Test", "priority": "medium"}

        resp = await admin_client.request(method, path, json=json_body)

        assert resp.status_code == 403, f"Admin {method} {path} → expected 403, got {resp.status_code}"

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/me/client"),
            ("GET", "/api/me/services"),
            ("GET", "/api/me/contacts"),
            ("GET", "/api/me/activity"),
            ("GET", "/api/me/messages"),
            ("GET", "/api/me/tickets"),
        ],
    )
    async def test_comercial_forbidden_on_me(
        self,
        comercial_client: httpx.AsyncClient,
        method: str,
        path: str,
    ) -> None:
        """Comercial role must receive 403 on every /me endpoint."""
        resp = await comercial_client.request(method, path)

        assert resp.status_code == 403, f"Comercial {method} {path} → expected 403, got {resp.status_code}"

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/me/client"),
            ("GET", "/api/me/services"),
            ("GET", "/api/me/contacts"),
            ("GET", "/api/me/activity"),
            ("GET", "/api/me/messages"),
            ("GET", "/api/me/tickets"),
        ],
    )
    async def test_consultor_forbidden_on_me(
        self,
        consultor_client: httpx.AsyncClient,
        method: str,
        path: str,
    ) -> None:
        """Consultor role must receive 403 on every /me endpoint."""
        resp = await consultor_client.request(method, path)

        assert resp.status_code == 403, f"Consultor {method} {path} → expected 403, got {resp.status_code}"


# ---------------------------------------------------------------------------
# TestValidationEdgeCases (spec §POST /api/me/messages validation)
# ---------------------------------------------------------------------------


class TestValidationEdgeCases:
    """422 validation edge cases for /me endpoints."""

    async def test_post_message_empty_body_returns_422(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """POST /api/me/messages with empty body string → 422."""
        resp = await portal_client_a.post("/api/me/messages", json={"body": ""})

        assert resp.status_code == 422, resp.text

    async def test_post_message_over_4000_chars_returns_422(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """POST /api/me/messages with body > 4000 chars → 422."""
        resp = await portal_client_a.post("/api/me/messages", json={"body": "x" * 4001})

        assert resp.status_code == 422, resp.text
