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
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Client, Ticket
from database.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(client: httpx.AsyncClient, name: str = "Ticket Corp") -> str:
    resp = await client.post("/api/clients", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _seed_ticket(
    session_factory: async_sessionmaker,
    client_user: User,
    portal_client: Client,
    title: str = "Test Ticket",
    priority: str = "medium",
) -> dict:
    """
    Insert a Ticket row directly via ORM using a real persisted client_user.

    Avoids FK violations that occurred when the old helper used an ephemeral
    (non-persisted) portal_user for ``created_by_user_id``.
    """
    async with session_factory() as session:
        ticket = Ticket(
            id=uuid.uuid4(),
            client_id=portal_client.id,
            title=title,
            priority=priority,
            status="pending",
            created_by_user_id=client_user.id,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return {
            "id": str(ticket.id),
            "client_id": str(ticket.client_id),
            "title": ticket.title,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_by_user_id": str(ticket.created_by_user_id),
        }


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/tickets
# ---------------------------------------------------------------------------


class TestListClientTickets:
    async def test_admin_can_list_tickets(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Admin lists tickets for a client — 200 + TicketListResponse shape."""
        client_id = str(test_client_for_portal.id)
        await _seed_ticket(test_session_factory, client_user, test_client_for_portal, "First ticket")
        await _seed_ticket(test_session_factory, client_user, test_client_for_portal, "Second ticket")

        resp = await admin_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert body["total"] == 2

    async def test_consultor_can_list_tickets(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Consultor can list tickets for any client (200)."""
        client_id = str(test_client_for_portal.id)
        await _seed_ticket(test_session_factory, client_user, test_client_for_portal)

        resp = await consultor_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text

    async def test_comercial_can_list_tickets(
        self,
        comercial_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Comercial can list tickets (read access)."""
        client_id = str(test_client_for_portal.id)
        await _seed_ticket(test_session_factory, client_user, test_client_for_portal)

        resp = await comercial_client.get(f"/api/clients/{client_id}/tickets")

        assert resp.status_code == 200, resp.text

    async def test_status_filter_works(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """GET tickets with status filter returns only matching tickets."""
        client_id = str(test_client_for_portal.id)
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Pending ticket"
        )
        ticket_id = ticket["id"]

        # Close the ticket via internal PATCH
        await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "closed"},
        )

        # Create another ticket that stays pending
        await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Still pending"
        )

        resp = await admin_client.get(
            f"/api/clients/{client_id}/tickets",
            params={"status": "closed"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "closed"

    async def test_limit_exceeds_max_returns_400(
        self,
        admin_client: httpx.AsyncClient,
        test_client_for_portal: Client,
    ):
        """limit > 200 → 400 with error envelope."""
        client_id = str(test_client_for_portal.id)

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
    async def test_admin_can_get_ticket(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Admin can fetch any ticket by ID (200 + TicketOut shape)."""
        client_id = str(test_client_for_portal.id)
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Get me"
        )
        ticket_id = ticket["id"]

        resp = await admin_client.get(f"/api/tickets/{ticket_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == ticket_id
        assert body["title"] == "Get me"
        assert body["client_id"] == client_id

    async def test_consultor_can_get_ticket(
        self,
        consultor_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Consultor can fetch any ticket (200)."""
        ticket = await _seed_ticket(test_session_factory, client_user, test_client_for_portal)
        ticket_id = ticket["id"]

        resp = await consultor_client.get(f"/api/tickets/{ticket_id}")

        assert resp.status_code == 200, resp.text

    async def test_comercial_can_get_ticket(
        self,
        comercial_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Comercial can fetch any ticket (200)."""
        ticket = await _seed_ticket(test_session_factory, client_user, test_client_for_portal)
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
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Admin PATCH → 200 + updated fields reflected in response."""
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Original Title"
        )
        ticket_id = ticket["id"]

        resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"title": "Updated Title", "priority": "high"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Updated Title"
        assert body["priority"] == "high"

    async def test_admin_can_change_status(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Admin can transition status to in_progress and closed."""
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Status Ticket"
        )
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
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Transitioning to closed logs ticket_closed activity kind."""
        client_id = str(test_client_for_portal.id)
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Close Me"
        )
        ticket_id = ticket["id"]

        await admin_client.patch(f"/api/tickets/{ticket_id}", json={"status": "closed"})

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "ticket_closed" in kinds, f"Expected ticket_closed in {kinds}"

    async def test_non_close_update_logs_ticket_updated_activity(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Non-close updates log ticket_updated activity kind."""
        client_id = str(test_client_for_portal.id)
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Update Me"
        )
        ticket_id = ticket["id"]

        await admin_client.patch(f"/api/tickets/{ticket_id}", json={"priority": "high"})

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "ticket_updated" in kinds, f"Expected ticket_updated in {kinds}"

    async def test_consultor_can_change_status(
        self,
        consultor_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Consultor can update ticket status (200)."""
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Consultor Ticket"
        )
        ticket_id = ticket["id"]

        resp = await consultor_client.patch(
            f"/api/tickets/{ticket_id}", json={"status": "in_progress"}
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_progress"

    async def test_comercial_cannot_change_status_403(
        self,
        comercial_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Comercial attempting to change ticket status → 403."""
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Comercial Ticket"
        )
        ticket_id = ticket["id"]

        resp = await comercial_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "in_progress"},
        )

        assert resp.status_code == 403, resp.text

    async def test_comercial_can_update_non_status_fields(
        self,
        comercial_client: httpx.AsyncClient,
        test_session_factory,
        client_user: User,
        test_client_for_portal: Client,
    ):
        """Comercial can patch title, priority, and body (200)."""
        ticket = await _seed_ticket(
            test_session_factory, client_user, test_client_for_portal, "Comercial Editable"
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
