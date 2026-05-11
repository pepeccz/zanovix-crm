"""
Integration tests — Milestones CRUD (TASK-33).

Coverage:
- POST /api/services/{id}/milestones:
    - Creates with `n` ordering field
    - Shape is MilestoneRead
- PATCH /api/services/{id}/milestones/{n}:
    - Completing (setting completed_at) → writes activity_log "milestone_completed"
    - Updating without flipping completed_at → no milestone_completed in log
- DELETE /api/services/{id}/milestones/{n}:
    - Admin → 204
    - Non-admin (comercial) → 403
"""

from __future__ import annotations

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(client: httpx.AsyncClient, name: str = "Milestone Parent Corp") -> str:
    resp = await client.post("/api/clients", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_service(client: httpx.AsyncClient, client_id: str, title: str = "MS Service") -> dict:
    resp = await client.post(
        f"/api/clients/{client_id}/services",
        json={"type": "development", "title": title, "client_id": client_id},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_milestone(
    client: httpx.AsyncClient, service_id: str, n: int = 1, title: str = "Milestone"
) -> dict:
    resp = await client.post(
        f"/api/services/{service_id}/milestones",
        json={"n": n, "title": title},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/services/{id}/milestones
# ---------------------------------------------------------------------------


class TestCreateMilestone:
    async def test_create_returns_201_and_shape(self, admin_client: httpx.AsyncClient):
        """POST milestone returns 201 + MilestoneRead shape with n ordering."""
        client_id = await _create_client(admin_client, "MS Create Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]

        resp = await admin_client.post(
            f"/api/services/{svc_id}/milestones",
            json={"n": 1, "title": "Discovery Phase", "due_date": "2026-06-30"},
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["n"] == 1
        assert body["title"] == "Discovery Phase"
        assert body["due_date"] == "2026-06-30"
        assert body["completed_at"] is None
        assert "id" in body
        assert "service_id" in body
        assert body["service_id"] == svc_id

    async def test_create_multiple_preserves_n_ordering(
        self, admin_client: httpx.AsyncClient
    ):
        """Multiple milestones are retrievable with their `n` values intact."""
        client_id = await _create_client(admin_client, "MS Order Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]

        await _create_milestone(admin_client, svc_id, n=1, title="Step 1")
        await _create_milestone(admin_client, svc_id, n=2, title="Step 2")
        await _create_milestone(admin_client, svc_id, n=3, title="Step 3")

        resp = await admin_client.get(f"/api/services/{svc_id}")
        milestones = resp.json()["milestones"]

        assert len(milestones) == 3
        ns = [m["n"] for m in milestones]
        assert sorted(ns) == [1, 2, 3]


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}/milestones/{n}
# ---------------------------------------------------------------------------


class TestUpdateMilestone:
    async def test_completing_milestone_writes_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """Setting completed_at for the first time writes 'milestone_completed' activity."""
        client_id = await _create_client(admin_client, "MS Complete Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]
        await _create_milestone(admin_client, svc_id, n=1, title="To Complete")

        resp = await admin_client.patch(
            f"/api/services/{svc_id}/milestones/1",
            json={"completed_at": "2026-05-11T10:00:00Z"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["completed_at"] is not None

        # Verify activity_log
        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "milestone_completed" in kinds, f"Expected milestone_completed in {kinds}"

    async def test_updating_title_without_completion_no_milestone_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """
        Patching a milestone without flipping completed_at does NOT write
        a 'milestone_completed' activity log entry.
        """
        client_id = await _create_client(admin_client, "MS No Activity Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]
        await _create_milestone(admin_client, svc_id, n=1, title="Original Title")

        # Count activity entries before
        detail_resp_before = await admin_client.get(f"/api/clients/{client_id}")
        activity_before = detail_resp_before.json()["recent_activity"]
        count_before = len(activity_before)

        # Patch title only (no completed_at change)
        resp = await admin_client.patch(
            f"/api/services/{svc_id}/milestones/1",
            json={"title": "Renamed Title"},
        )
        assert resp.status_code == 200, resp.text

        # Check activity after: no new milestone_completed entry
        detail_resp_after = await admin_client.get(f"/api/clients/{client_id}")
        activity_after = detail_resp_after.json()["recent_activity"]

        milestone_completed_entries = [
            a for a in activity_after if a["kind"] == "milestone_completed"
        ]
        assert len(milestone_completed_entries) == 0, (
            "Expected no milestone_completed activity after title-only patch"
        )

    async def test_patch_404_for_missing_milestone(self, admin_client: httpx.AsyncClient):
        """PATCH with nonexistent n → 404."""
        client_id = await _create_client(admin_client, "MS 404 Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]

        resp = await admin_client.patch(
            f"/api/services/{svc_id}/milestones/99",
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# DELETE /api/services/{id}/milestones/{n}
# ---------------------------------------------------------------------------


class TestDeleteMilestone:
    async def test_admin_deletes_milestone_204(self, admin_client: httpx.AsyncClient):
        """Admin can delete a milestone → 204 No Content."""
        client_id = await _create_client(admin_client, "MS Delete Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]
        await _create_milestone(admin_client, svc_id, n=1, title="To Delete")

        resp = await admin_client.delete(f"/api/services/{svc_id}/milestones/1")
        assert resp.status_code == 204, resp.text

        # Verify gone
        svc_resp = await admin_client.get(f"/api/services/{svc_id}")
        assert svc_resp.json()["milestones"] == []

    async def test_comercial_cannot_delete_milestone_403(
        self,
        comercial_client: httpx.AsyncClient,
        admin_client: httpx.AsyncClient,
    ):
        """Comercial cannot delete milestones (admin-only) → 403."""
        client_id = await _create_client(admin_client, "MS RBAC Corp")
        svc = await _create_service(admin_client, client_id)
        svc_id = svc["id"]
        await _create_milestone(admin_client, svc_id, n=1, title="Protected MS")

        resp = await comercial_client.delete(f"/api/services/{svc_id}/milestones/1")
        assert resp.status_code == 403, resp.text
