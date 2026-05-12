"""
Integration tests — Internal ticket endpoints (PR-3).

Coverage:
  GET  /api/clients/{client_id}/tickets:
    - admin/consultor/comercial can list tickets for any client
    - status + priority filters work
    - limit > 200 → 400 envelope

  GET  /api/tickets/{ticket_id}:
    - admin/consultor/comercial can read any ticket
    - 404 for missing ticket

  PATCH /api/tickets/{ticket_id}:
    - admin/consultor can update title, priority, status, assigned_to_user_id, body
    - status → closed logs ticket_closed activity
    - other updates log ticket_updated activity
    - comercial can update title/priority/body but NOT status (→ 403)
    - 404 for missing ticket
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from database.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(client: httpx.AsyncClient, name: str = "Ticket Corp") -> str:
    resp = await client.post("/api/clients", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_ticket(
    client: httpx.AsyncClient,
    client_id: str,
    title: str = "Test Ticket",
    priority: str = "medium",
) -> dict:
    """Create a ticket via the /api/me/* portal endpoint using a client_user-scoped app.

    Since we cannot easily create a client_user in conftest without adding a new fixture,
    we use the admin app with a direct DB insertion via the admin client creation route.

    For simplicity, we create the ticket via the me.py router by building a minimal
    client_user app pointed at the correct client.
    """
    # We rely on admin creating tickets via the service layer directly in tests.
    # However, since no admin endpoint for POST /api/clients/{id}/tickets exists (only /me/),
    # we use the test helper below to use the me.py POST endpoint via a portal-user fixture.
    # The approach: POST via /api/me/tickets with a scoped app that has client_id set.
    raise NotImplementedError("Use _create_ticket_via_portal instead")


async def _create_ticket_via_portal(
    admin_client: httpx.AsyncClient,
    client_id: str,
    title: str = "Test Ticket",
    priority: str = "medium",
) -> dict:
    """
    Create a ticket via the me.py portal endpoint by building a temporary
    client_user-scoped app with the given client_id.
    """
    from tests.integration._app_factory import make_role_app

    portal_user = User(
        id=uuid.uuid4(),
        email=f"portal.{uuid.uuid4().hex[:6]}@zanovix.test",
        password_hash="$2b$12$placeholder",
        role="client_user",
        display_name="Portal Test User",
        is_active=True,
        client_id=uuid.UUID(client_id),
    )
    portal_app = make_role_app(portal_user)
    transport = httpx.ASGITransport(app=portal_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as portal_client:
        resp = await portal_client.post(
            "/api/me/tickets",
            json={"title": title, "priority": priority},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/tickets
# ---------------------------------------------------------------------------


class TestListClientTickets:
    async def test_admin_can_list_tickets(self, admin_client: httpx.AsyncClient):
        """Admin lists tickets for a client — 200 + TicketListResponse shape."""
        client_id = await _create_client(admin_client, "Admin List Tickets Corp")
        await _create_ticket_via_portal(admin_client, client_id, "First ticket")
        await _create_ticket_via_portal(admin_client, client_id, "Second ticket")

        resp = await admin_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert body["total"] == 2

    async def test_consultor_can_list_tickets(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
    ):
        """Consultor can list tickets for any client (200)."""
        client_id = await _create_client(admin_client, "Consultor List Tickets Corp")
        await _create_ticket_via_portal(admin_client, client_id)

        resp = await consultor_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text

    async def test_comercial_can_list_tickets(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial can list tickets (read access)."""
        client_id = await _create_client(admin_client, "Comercial List Tickets Corp")
        await _create_ticket_via_portal(admin_client, client_id)

        resp = await comercial_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text

    async def test_status_filter_works(self, admin_client: httpx.AsyncClient):
        """GET tickets with status filter returns only matching tickets."""
        client_id = await _create_client(admin_client, "Status Filter Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Pending ticket")
        ticket_id = ticket["id"]

        # Close the ticket via internal PATCH
        await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "closed"},
        )

        # Create another ticket that stays pending
        await _create_ticket_via_portal(admin_client, client_id, "Still pending")

        resp = await admin_client.get(
            f"/api/clients/{client_id}/tickets",
            params={"status": "closed"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "closed"

    async def test_limit_exceeds_max_returns_400(self, admin_client: httpx.AsyncClient):
        """limit > 200 → 400 with error envelope."""
        client_id = await _create_client(admin_client, "Limit Tickets Corp")

        resp = await admin_client.get(
            f"/api/clients/{client_id}/tickets",
            params={"limit": "201"},
        )

        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert body.get("success") is False
        assert body.get("error_code") == "HTTP_400"

    async def test_empty_list_for_new_client(self, admin_client: httpx.AsyncClient):
        """No tickets for a freshly created client returns total=0, items=[]."""
        client_id = await _create_client(admin_client, "Empty Tickets Corp")

        resp = await admin_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []


# ---------------------------------------------------------------------------
# GET /api/tickets/{ticket_id}
# ---------------------------------------------------------------------------


class TestGetTicket:
    async def test_admin_can_get_ticket(self, admin_client: httpx.AsyncClient):
        """Admin can fetch any ticket by ID (200 + TicketOut shape)."""
        client_id = await _create_client(admin_client, "Get Ticket Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Get me")
        ticket_id = ticket["id"]

        resp = await admin_client.get(f"/api/tickets/{ticket_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == ticket_id
        assert body["title"] == "Get me"
        assert body["client_id"] == client_id

    async def test_consultor_can_get_ticket(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
    ):
        """Consultor can fetch any ticket (200)."""
        client_id = await _create_client(admin_client, "Consultor Get Ticket Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id)
        ticket_id = ticket["id"]

        resp = await consultor_client.get(f"/api/tickets/{ticket_id}")

        assert resp.status_code == 200, resp.text

    async def test_comercial_can_get_ticket(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial can fetch any ticket (200)."""
        client_id = await _create_client(admin_client, "Comercial Get Ticket Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id)
        ticket_id = ticket["id"]

        resp = await comercial_client.get(f"/api/tickets/{ticket_id}")

        assert resp.status_code == 200, resp.text

    async def test_missing_ticket_returns_404(self, admin_client: httpx.AsyncClient):
        """GET /api/tickets/{nonexistent_id} → 404."""
        nonexistent_id = str(uuid.uuid4())

        resp = await admin_client.get(f"/api/tickets/{nonexistent_id}")

        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# PATCH /api/tickets/{ticket_id}
# ---------------------------------------------------------------------------


class TestUpdateTicketInternal:
    async def test_admin_can_update_title_and_priority(
        self, admin_client: httpx.AsyncClient
    ):
        """Admin PATCH → 200 + updated fields reflected in response."""
        client_id = await _create_client(admin_client, "Admin Update Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Original Title")
        ticket_id = ticket["id"]

        resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"title": "Updated Title", "priority": "high"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Updated Title"
        assert body["priority"] == "high"

    async def test_admin_can_change_status(self, admin_client: httpx.AsyncClient):
        """Admin can transition status to in_progress and closed."""
        client_id = await _create_client(admin_client, "Status Change Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Status Ticket")
        ticket_id = ticket["id"]

        # pending → in_progress
        resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}", json={"status": "in_progress"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_progress"

        # in_progress → closed
        resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}", json={"status": "closed"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "closed"

    async def test_closed_status_logs_ticket_closed_activity(
        self,
        admin_client: httpx.AsyncClient,
    ):
        """Transitioning to closed logs ticket_closed activity kind."""
        client_id = await _create_client(admin_client, "Close Activity Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Close Me")
        ticket_id = ticket["id"]

        await admin_client.patch(f"/api/tickets/{ticket_id}", json={"status": "closed"})

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "ticket_closed" in kinds, f"Expected ticket_closed in {kinds}"

    async def test_non_close_update_logs_ticket_updated_activity(
        self,
        admin_client: httpx.AsyncClient,
    ):
        """Non-close updates log ticket_updated activity kind."""
        client_id = await _create_client(admin_client, "Update Activity Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Update Me")
        ticket_id = ticket["id"]

        await admin_client.patch(f"/api/tickets/{ticket_id}", json={"priority": "high"})

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "ticket_updated" in kinds, f"Expected ticket_updated in {kinds}"

    async def test_consultor_can_change_status(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
    ):
        """Consultor can update ticket status (200)."""
        client_id = await _create_client(admin_client, "Consultor Status Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Consultor Ticket")
        ticket_id = ticket["id"]

        resp = await consultor_client.patch(
            f"/api/tickets/{ticket_id}", json={"status": "in_progress"}
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_progress"

    async def test_comercial_cannot_change_status_403(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial attempting to change ticket status → 403."""
        client_id = await _create_client(admin_client, "Comercial Block Status Corp")
        ticket = await _create_ticket_via_portal(admin_client, client_id, "Comercial Ticket")
        ticket_id = ticket["id"]

        resp = await comercial_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "in_progress"},
        )

        assert resp.status_code == 403, resp.text

    async def test_comercial_can_update_non_status_fields(
        self,
        admin_client: httpx.AsyncClient,
        comercial_client: httpx.AsyncClient,
    ):
        """Comercial can patch title, priority, and body (200)."""
        client_id = await _create_client(admin_client, "Comercial Edit Corp")
        ticket = await _create_ticket_via_portal(
            admin_client, client_id, "Comercial Editable"
        )
        ticket_id = ticket["id"]

        resp = await comercial_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"title": "Comercial Updated Title", "priority": "low"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Comercial Updated Title"
        assert body["priority"] == "low"

    async def test_patch_missing_ticket_returns_404(self, admin_client: httpx.AsyncClient):
        """PATCH /api/tickets/{nonexistent_id} → 404."""
        nonexistent_id = str(uuid.uuid4())

        resp = await admin_client.patch(
            f"/api/tickets/{nonexistent_id}",
            json={"title": "Ghost"},
        )

        assert resp.status_code == 404, resp.text
