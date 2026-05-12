"""
Integration tests — /api/me/activity client isolation (PR-4).

Verifies that GET /api/me/activity returns ONLY activity entries for the
authenticated client_user's client, never entries from another client.

Spec §activity-log-kinds-enum-extension — ticket_opened / ticket_closed /
ticket_updated / message_sent activity kinds are produced correctly and are
returned in /me/activity scoped to the owning client.

Coverage:
  - Seed activities on client_A and client_B.
  - Authenticate as client_user_A; assert only client_A entries returned.
  - Activity kinds written by ticket/message operations are visible in /me/activity.
  - Pagination shape is correct (items + total + limit + offset).
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Client, Service, Ticket
from database.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_ticket(
    session_factory: async_sessionmaker,
    client: Client,
    creator: User,
    title: str = "Activity Ticket",
) -> dict:
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
        return {"id": str(ticket.id), "client_id": str(ticket.client_id)}


async def _seed_service(
    session_factory: async_sessionmaker,
    client: Client,
    owner: User,
    title: str = "Activity Service",
) -> Service:
    async with session_factory() as session:
        svc = Service(
            id=uuid.uuid4(),
            client_id=client.id,
            owner_id=owner.id,
            type="development",
            title=title,
            state="scoping",
        )
        session.add(svc)
        await session.commit()
        await session.refresh(svc)
        return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMeActivityIsolation:
    """Verify /api/me/activity only returns entries belonging to the caller's client."""

    async def test_activity_list_returns_200_and_pagination_shape(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """GET /api/me/activity → 200 with pagination envelope."""
        resp = await portal_client_a.get("/api/me/activity")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body

    async def test_activity_empty_for_fresh_client(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """A freshly seeded client with no activity returns total=0."""
        resp = await portal_client_a.get("/api/me/activity")

        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    async def test_activity_contains_ticket_opened_after_portal_create(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """POST /api/me/tickets logs ticket_opened; visible in /me/activity."""
        resp = await portal_client_a.post(
            "/api/me/tickets",
            json={"title": "Activity Test Ticket", "priority": "low"},
        )
        assert resp.status_code == 201, resp.text

        activity_resp = await portal_client_a.get("/api/me/activity")
        assert activity_resp.status_code == 200, activity_resp.text
        kinds = [a["kind"] for a in activity_resp.json()["items"]]
        assert "ticket_opened" in kinds, f"Expected ticket_opened in {kinds}"

    async def test_activity_contains_message_sent_after_portal_send(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
    ) -> None:
        """POST /api/me/messages logs message_sent; visible in /me/activity."""
        resp = await portal_client_a.post(
            "/api/me/messages",
            json={"body": "Hello from portal activity test"},
        )
        assert resp.status_code == 201, resp.text

        activity_resp = await portal_client_a.get("/api/me/activity")
        assert activity_resp.status_code == 200, activity_resp.text
        kinds = [a["kind"] for a in activity_resp.json()["items"]]
        assert "message_sent" in kinds, f"Expected message_sent in {kinds}"

    async def test_activity_no_cross_client_data(
        self,
        portal_client_a: httpx.AsyncClient,
        test_client_for_portal: Client,
        test_client_for_portal_b: Client,
        test_session_factory: async_sessionmaker,
        client_user_b: User,
    ) -> None:
        """
        Seed a ticket on client_B via ORM (triggers ticket_opened activity for B).
        Authenticate as client_user_A and assert the B activity is NOT in /me/activity.
        """
        # Create a ticket on client A first via the portal endpoint to ensure A has
        # at least one activity, and also create one on B directly via ORM.
        resp_a = await portal_client_a.post(
            "/api/me/tickets",
            json={"title": "Client A Ticket"},
        )
        assert resp_a.status_code == 201, resp_a.text
        ticket_a_id = resp_a.json()["id"]

        # Seed a ticket for client_B (ORM insert — no HTTP; client_user_A has no
        # portal access to client_B's ticket endpoint).
        ticket_b = await _seed_ticket(
            test_session_factory,
            test_client_for_portal_b,
            client_user_b,
            "Client B Secret Ticket",
        )

        # Fetch client_A activity
        activity_resp = await portal_client_a.get("/api/me/activity")
        assert activity_resp.status_code == 200, activity_resp.text
        body = activity_resp.json()

        # Every returned entry must belong to client_A
        for entry in body["items"]:
            assert entry["client_id"] == str(test_client_for_portal.id), (
                f"Activity entry {entry['id']} belongs to {entry['client_id']}, "
                f"not to client_A ({test_client_for_portal.id})"
            )

    async def test_activity_ticket_updated_kind_visible(
        self,
        portal_client_a: httpx.AsyncClient,
        admin_client: httpx.AsyncClient,
        test_client_for_portal: Client,
        test_session_factory: async_sessionmaker,
        client_user: User,
    ) -> None:
        """Internal PATCH of a ticket that does NOT close it logs ticket_updated."""
        ticket = await _seed_ticket(
            test_session_factory, test_client_for_portal, client_user, "Update Kind Ticket"
        )
        ticket_id = ticket["id"]

        # Admin updates priority (not status → ticket_updated, not ticket_closed)
        patch_resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"priority": "high"},
        )
        assert patch_resp.status_code == 200, patch_resp.text

        # Check via /me/activity as client_user_A
        activity_resp = await portal_client_a.get("/api/me/activity")
        assert activity_resp.status_code == 200, activity_resp.text
        kinds = [a["kind"] for a in activity_resp.json()["items"]]
        assert "ticket_updated" in kinds, f"Expected ticket_updated in {kinds}"

    async def test_activity_ticket_closed_kind_visible(
        self,
        portal_client_a: httpx.AsyncClient,
        admin_client: httpx.AsyncClient,
        test_client_for_portal: Client,
        test_session_factory: async_sessionmaker,
        client_user: User,
    ) -> None:
        """Internal PATCH to status=closed logs ticket_closed."""
        ticket = await _seed_ticket(
            test_session_factory, test_client_for_portal, client_user, "Close Kind Ticket"
        )
        ticket_id = ticket["id"]

        patch_resp = await admin_client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "closed"},
        )
        assert patch_resp.status_code == 200, patch_resp.text

        activity_resp = await portal_client_a.get("/api/me/activity")
        assert activity_resp.status_code == 200, activity_resp.text
        kinds = [a["kind"] for a in activity_resp.json()["items"]]
        assert "ticket_closed" in kinds, f"Expected ticket_closed in {kinds}"
