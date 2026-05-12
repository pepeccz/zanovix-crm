"""
Integration tests — Internal message endpoints (PR-3).

Coverage:
  GET  /api/clients/{id}/messages:
    - admin can list messages for any client (200 + MessageListResponse)
    - consultor can list messages for any client (200)
    - comercial can list messages (200 — read-only access)
    - client_user cannot access internal endpoint (403)
    - limit > 200 → 400 with {success: false, error_code: HTTP_400} envelope

  POST /api/clients/{id}/messages:
    - admin reply → 201 + MessageOut, sender_user_id == admin.id
    - consultor reply → 201 + MessageOut
    - comercial cannot POST (403)
    - empty body → 422 validation error
    - non-existent client → handled by DB FK (404 or 500 is acceptable; test not required)
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from database.models.user import User
from tests.integration._app_factory import make_role_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(client: httpx.AsyncClient, name: str = "Message Corp") -> str:
    resp = await client.post("/api/clients", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _post_message(
    client: httpx.AsyncClient,
    client_id: str,
    body: str = "Hello from admin",
) -> dict:
    resp = await client.post(
        f"/api/clients/{client_id}/messages",
        json={"body": body},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/clients/{id}/messages
# ---------------------------------------------------------------------------


class TestListClientMessages:
    async def test_admin_can_list_messages(
        self,
        admin_client: httpx.AsyncClient,
    ):
        """Admin can list messages for any client — returns 200 + MessageListResponse shape."""
        client_id = await _create_client(admin_client, "Admin List Corp")
        await _post_message(admin_client, client_id, "First message")
        await _post_message(admin_client, client_id, "Second message")

        resp = await admin_client.get(f"/api/clients/{client_id}/messages")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] == 2
        assert len(body["items"]) == 2
        bodies = {m["body"] for m in body["items"]}
        assert bodies == {"First message", "Second message"}

    async def test_consultor_can_list_messages(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
    ):
        """Consultor can list messages for any client (200)."""
        client_id = await _create_client(admin_client, "Consultor List Corp")
        await _post_message(admin_client, client_id, "Admin reply")

        resp = await consultor_client.get(f"/api/clients/{client_id}/messages")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1

    async def test_comercial_can_list_messages(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial can read messages but not create them."""
        client_id = await _create_client(admin_client, "Comercial List Corp")
        await _post_message(admin_client, client_id, "Admin message")

        resp = await comercial_client.get(f"/api/clients/{client_id}/messages")

        assert resp.status_code == 200, resp.text

    async def test_client_user_cannot_access_internal_messages_403(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ):
        """client_user calling internal GET /api/clients/{id}/messages → 403."""
        client_id = await _create_client(admin_client, "Client Block Corp")

        # Build a client_user app
        client_user = User(
            id=uuid.uuid4(),
            email="portal.user@zanovix.test",
            password_hash="$2b$12$placeholder",
            role="client_user",
            display_name="Portal User",
            is_active=True,
            client_id=None,
        )
        portal_app = make_role_app(client_user)
        import httpx as _httpx
        transport = _httpx.ASGITransport(app=portal_app)
        async with _httpx.AsyncClient(transport=transport, base_url="http://test") as portal_client:
            resp = await portal_client.get(f"/api/clients/{client_id}/messages")
            assert resp.status_code == 403, resp.text

    async def test_list_empty_for_new_client(self, admin_client: httpx.AsyncClient):
        """No messages for a new client returns total=0, items=[]."""
        client_id = await _create_client(admin_client, "Empty Messages Corp")

        resp = await admin_client.get(f"/api/clients/{client_id}/messages")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    async def test_limit_exceeds_max_returns_400(self, admin_client: httpx.AsyncClient):
        """limit > 200 → 400 with error envelope."""
        client_id = await _create_client(admin_client, "Limit Test Corp")

        resp = await admin_client.get(
            f"/api/clients/{client_id}/messages",
            params={"limit": "201"},
        )

        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert body.get("success") is False
        assert body.get("error_code") == "HTTP_400"


# ---------------------------------------------------------------------------
# POST /api/clients/{id}/messages
# ---------------------------------------------------------------------------


class TestCreateClientMessage:
    async def test_admin_reply_returns_201_and_shape(
        self,
        admin_client: httpx.AsyncClient,
        admin_user: User,
    ):
        """Admin POST message → 201 + MessageOut with sender_user_id == admin.id."""
        client_id = await _create_client(admin_client, "Admin Reply Corp")

        resp = await admin_client.post(
            f"/api/clients/{client_id}/messages",
            json={"body": "Hello from admin"},
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["body"] == "Hello from admin"
        assert body["client_id"] == client_id
        assert body["sender_user_id"] == str(admin_user.id)
        assert "id" in body
        assert "created_at" in body

    async def test_consultor_reply_returns_201(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
        consultor_user: User,
    ):
        """Consultor POST message → 201 + sender_user_id == consultor.id."""
        client_id = await _create_client(admin_client, "Consultor Reply Corp")

        resp = await consultor_client.post(
            f"/api/clients/{client_id}/messages",
            json={"body": "Hello from consultor"},
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["sender_user_id"] == str(consultor_user.id)

    async def test_comercial_cannot_create_message_403(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial cannot POST messages to internal endpoint — 403."""
        client_id = await _create_client(admin_client, "Comercial Block Corp")

        resp = await comercial_client.post(
            f"/api/clients/{client_id}/messages",
            json={"body": "Should be blocked"},
        )

        assert resp.status_code == 403, resp.text

    async def test_empty_body_returns_422(self, admin_client: httpx.AsyncClient):
        """POST message with empty body → 422 validation error."""
        client_id = await _create_client(admin_client, "Empty Body Corp")

        resp = await admin_client.post(
            f"/api/clients/{client_id}/messages",
            json={"body": ""},
        )

        assert resp.status_code == 422, resp.text

    async def test_message_appears_in_list_after_create(
        self,
        admin_client: httpx.AsyncClient,
    ):
        """Created message appears in subsequent GET list."""
        client_id = await _create_client(admin_client, "Round Trip Corp")
        await _post_message(admin_client, client_id, "Round trip message")

        resp = await admin_client.get(f"/api/clients/{client_id}/messages")

        assert resp.status_code == 200, resp.text
        body_texts = [m["body"] for m in resp.json()["items"]]
        assert "Round trip message" in body_texts
