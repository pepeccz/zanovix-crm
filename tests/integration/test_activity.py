"""
Integration tests — GET /api/activity (PR 1).

Coverage:
- GET /api/activity:
    - admin gets 200 with correct ActivityLogListResponse shape
    - 403 for non-admin role (consultor)
    - limit > 200 → 400 with {error: limit_exceeds_max, max: 200}
    - ?client_id filter returns only entries for that client
    - default limit = 50 when no limit param is provided
    - ordering is newest-first (created_at DESC)
"""

from __future__ import annotations

import uuid

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(admin_client: httpx.AsyncClient, name: str) -> str:
    """Create a client and return its id."""
    resp = await admin_client.post(
        "/api/clients",
        json={"name": name, "stage": "lead"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _stage_transition(
    admin_client: httpx.AsyncClient,
    client_id: str,
    stage: str,
) -> None:
    """Trigger a stage transition to generate an ActivityLog entry."""
    resp = await admin_client.patch(
        f"/api/clients/{client_id}/stage",
        json={"stage": stage},
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# GET /api/activity
# ---------------------------------------------------------------------------


class TestGetActivity:
    async def test_admin_gets_200_with_correct_shape(
        self, admin_client: httpx.AsyncClient
    ):
        """GET /api/activity returns 200 with ActivityLogListResponse shape."""
        resp = await admin_client.get("/api/activity")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert isinstance(body["items"], list)
        assert body["limit"] == 50   # default
        assert body["offset"] == 0

    async def test_consultor_gets_403(self, consultor_client: httpx.AsyncClient):
        """GET /api/activity returns 403 for non-admin role."""
        resp = await consultor_client.get("/api/activity")
        assert resp.status_code == 403, resp.text

    async def test_limit_exceeds_max_returns_400(
        self, admin_client: httpx.AsyncClient
    ):
        """limit > 200 returns 400 with unified error envelope, not 422."""
        resp = await admin_client.get("/api/activity?limit=201")

        assert resp.status_code == 400, resp.text
        body = resp.json()
        # Unified error handler (shared/fastapi_errors.py) converts HTTPException to
        # APIErrorResponse: {success, error_category, error_code, message, ...}
        assert body.get("success") is False
        assert body.get("error_code") == "HTTP_400"

    async def test_limit_at_max_is_allowed(self, admin_client: httpx.AsyncClient):
        """limit = 200 is the boundary — must return 200 OK."""
        resp = await admin_client.get("/api/activity?limit=200")
        assert resp.status_code == 200, resp.text
        assert resp.json()["limit"] == 200

    async def test_activity_appears_after_stage_transition(
        self, admin_client: httpx.AsyncClient
    ):
        """After a stage transition the entry appears in the activity feed."""
        client_id = await _create_client(admin_client, "Activity Test Corp")
        await _stage_transition(admin_client, client_id, "discovery_scheduled")

        resp = await admin_client.get("/api/activity")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        items = body["items"]
        assert len(items) >= 1

        # Validate individual entry shape
        entry = items[0]
        assert "id" in entry
        assert "created_at" in entry
        assert "client_id" in entry
        assert "kind" in entry
        assert "body" in entry
        assert "actor_user_id" in entry

    async def test_client_id_filter_returns_only_matching_entries(
        self, admin_client: httpx.AsyncClient
    ):
        """?client_id=<uuid> returns only entries for that client."""
        client_a_id = await _create_client(admin_client, "Client A for Filter")
        client_b_id = await _create_client(admin_client, "Client B for Filter")

        # Generate activity on both clients
        await _stage_transition(admin_client, client_a_id, "discovery_scheduled")
        await _stage_transition(admin_client, client_b_id, "discovery_scheduled")

        resp = await admin_client.get(f"/api/activity?client_id={client_a_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        # Every returned entry must belong to client_a
        for entry in body["items"]:
            assert entry["client_id"] == client_a_id

    async def test_ordering_newest_first(self, admin_client: httpx.AsyncClient):
        """Entries are returned in created_at DESC order (newest first)."""
        client_id = await _create_client(admin_client, "Ordering Test Corp")
        # Trigger two sequential transitions to get two distinct timestamps
        await _stage_transition(admin_client, client_id, "discovery_scheduled")
        await _stage_transition(admin_client, client_id, "discovery_done")

        resp = await admin_client.get(
            f"/api/activity?client_id={client_id}&limit=10"
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        assert len(items) >= 2

        timestamps = [item["created_at"] for item in items]
        # Verify strictly descending (or equal, for same-second inserts)
        assert timestamps == sorted(timestamps, reverse=True)
