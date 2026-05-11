"""
Integration tests — Services CRUD (TASK-32).

Coverage:
- POST /api/clients/{id}/services:
    - 201 + ServiceRead + activity_log "service_started"
    - POST under lost client → 422 CannotCreateOnLostClient
- GET /api/services (list):
    - {items, total, limit, offset} shape
    - state filter
    - type filter
    - client_id filter
- GET /api/services/{id}:
    - ServiceRead with milestones list
- PATCH /api/services/{id}:
    - service owner (consultor) → 200
    - other consultor → 404 (existence hiding, REQ-14-C)
- PATCH /api/services/{id}/state:
    - valid transition → 200 + activity_log "service_state_change"
    - invalid transition → 409 with allowed_transitions
"""

from __future__ import annotations

import uuid

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(
    client: httpx.AsyncClient, name: str = "Service Parent Corp", stage: str = "lead"
) -> str:
    resp = await client.post("/api/clients", json={"name": name, "stage": stage})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_service(
    client: httpx.AsyncClient,
    client_id: str,
    type: str = "assessment",
    title: str = "AI Assessment",
    owner_id: str | None = None,
) -> dict:
    payload: dict = {"type": type, "title": title, "client_id": client_id}
    if owner_id is not None:
        payload["owner_id"] = owner_id
    resp = await client.post(f"/api/clients/{client_id}/services", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/clients/{id}/services
# ---------------------------------------------------------------------------


class TestCreateService:
    async def test_create_returns_201_and_shape(self, admin_client: httpx.AsyncClient):
        """POST service returns 201 + ServiceRead shape."""
        client_id = await _create_client(admin_client, "Service Shape Corp")

        resp = await admin_client.post(
            f"/api/clients/{client_id}/services",
            json={
                "type": "development",
                "title": "CRM Dev Sprint",
                "setup_price_cents": 200000,
                "monthly_cents": 50000,
                "client_id": client_id,
            },
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["type"] == "development"
        assert body["title"] == "CRM Dev Sprint"
        assert body["state"] == "scoping"  # default initial state
        assert body["setup_price_cents"] == 200000
        assert body["monthly_cents"] == 50000
        assert body["client_id"] == client_id
        assert "id" in body
        assert "milestones" in body
        assert isinstance(body["milestones"], list)

    async def test_create_writes_service_started_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """Creating a service writes a 'service_started' activity_log entry."""
        client_id = await _create_client(admin_client, "Activity Service Corp")
        await _create_service(admin_client, client_id, title="Formation Sprint")

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]

        assert "service_started" in kinds, f"Expected service_started in {kinds}"

    async def test_create_on_lost_client_422(self, admin_client: httpx.AsyncClient):
        """POST service under a lost client → 422 with error=client_is_lost (REQ-16)."""
        client_id = await _create_client(admin_client, "Lost Client Corp", stage="lead")

        # Transition to lost
        await admin_client.patch(
            f"/api/clients/{client_id}/stage", json={"stage": "lost"}
        )

        resp = await admin_client.post(
            f"/api/clients/{client_id}/services",
            json={"type": "assessment", "title": "Should Fail", "client_id": client_id},
        )

        assert resp.status_code == 422, resp.text
        assert resp.json().get("error") == "client_is_lost"


# ---------------------------------------------------------------------------
# GET /api/services (list)
# ---------------------------------------------------------------------------


class TestListServices:
    async def test_list_returns_pagination_shape(self, admin_client: httpx.AsyncClient):
        """GET /api/services returns {items, total, limit, offset}."""
        client_id = await _create_client(admin_client, "List Services Corp")
        await _create_service(admin_client, client_id)

        resp = await admin_client.get("/api/services")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert isinstance(body["items"], list)
        assert body["total"] >= 1
        assert body["limit"] == 50
        assert body["offset"] == 0

    async def test_state_filter(self, admin_client: httpx.AsyncClient):
        """GET /api/services?state=scoping returns only scoping services."""
        client_id = await _create_client(admin_client, "State Filter Corp")
        svc = await _create_service(admin_client, client_id, title="Scoping Service")

        # Also create one in running state
        svc2 = await _create_service(admin_client, client_id, title="Running Service")
        await admin_client.patch(
            f"/api/services/{svc2['id']}/state",
            json={"state": "running"},
        )

        resp = await admin_client.get("/api/services?state=scoping")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(s["state"] == "scoping" for s in items)
        assert any(s["id"] == svc["id"] for s in items)

    async def test_type_filter(self, admin_client: httpx.AsyncClient):
        """GET /api/services?type=formation returns only formation services."""
        client_id = await _create_client(admin_client, "Type Filter Corp")
        formation_svc = await _create_service(
            admin_client, client_id, type="formation", title="Formation 101"
        )
        await _create_service(
            admin_client, client_id, type="assessment", title="Assessment"
        )

        resp = await admin_client.get("/api/services?type=formation")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(s["type"] == "formation" for s in items)
        assert any(s["id"] == formation_svc["id"] for s in items)

    async def test_client_id_filter(self, admin_client: httpx.AsyncClient):
        """GET /api/services?client_id=X returns only services for that client."""
        client_a_id = await _create_client(admin_client, "Client A")
        client_b_id = await _create_client(admin_client, "Client B")
        svc_a = await _create_service(admin_client, client_a_id, title="Service A")
        await _create_service(admin_client, client_b_id, title="Service B")

        resp = await admin_client.get(f"/api/services?client_id={client_a_id}")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(s["client_id"] == client_a_id for s in items)
        assert any(s["id"] == svc_a["id"] for s in items)


# ---------------------------------------------------------------------------
# GET /api/services/{id}
# ---------------------------------------------------------------------------


class TestGetServiceDetail:
    async def test_detail_returns_service_with_milestones(
        self, admin_client: httpx.AsyncClient
    ):
        """GET /api/services/{id} returns ServiceRead with nested milestones."""
        client_id = await _create_client(admin_client, "Detail Service Corp")
        svc = await _create_service(admin_client, client_id, title="Detailed Service")
        svc_id = svc["id"]

        # Add a milestone
        await admin_client.post(
            f"/api/services/{svc_id}/milestones",
            json={"n": 1, "title": "Kickoff"},
        )

        resp = await admin_client.get(f"/api/services/{svc_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == svc_id
        assert "milestones" in body
        assert isinstance(body["milestones"], list)
        assert len(body["milestones"]) == 1
        assert body["milestones"][0]["title"] == "Kickoff"
        assert body["milestones"][0]["n"] == 1

    async def test_detail_404_for_missing_service(self, admin_client: httpx.AsyncClient):
        """GET /api/services/{nonexistent} → 404."""
        resp = await admin_client.get(f"/api/services/{uuid.uuid4()}")
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# PATCH /api/services/{id} (metadata)
# ---------------------------------------------------------------------------


class TestUpdateServiceMetadata:
    async def test_service_owner_consultor_can_patch(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
        consultor_user,
    ):
        """Consultor who owns the service can PATCH metadata (REQ-14-B)."""
        client_id = await _create_client(admin_client, "Owner RBAC Corp")
        svc = await _create_service(
            admin_client, client_id, title="Consultor-Owned", owner_id=str(consultor_user.id)
        )
        svc_id = svc["id"]

        resp = await consultor_client.patch(
            f"/api/services/{svc_id}",
            json={"title": "Updated By Owner", "progress_pct": 30},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Updated By Owner"
        assert body["progress_pct"] == 30

    async def test_other_consultor_gets_404(
        self,
        admin_client: httpx.AsyncClient,
        consultor_client: httpx.AsyncClient,
        consultor_b_client: httpx.AsyncClient,
        consultor_b_user,
    ):
        """Consultor B cannot PATCH a service owned by Consultor A → 404 (existence hiding)."""
        client_id = await _create_client(admin_client, "Isolation Corp")
        svc = await _create_service(
            admin_client,
            client_id,
            title="Consultor A Service",
            owner_id=str(consultor_b_user.id),  # owned by B
        )
        svc_id = svc["id"]

        # Consultor A (consultor_client) tries to patch B's service
        resp = await consultor_client.patch(
            f"/api/services/{svc_id}",
            json={"title": "Should Fail"},
        )

        assert resp.status_code == 404, resp.text  # existence must not leak

    async def test_admin_can_patch_any_service(self, admin_client: httpx.AsyncClient):
        """Admin can PATCH any service regardless of owner."""
        client_id = await _create_client(admin_client, "Admin Patch Corp")
        svc = await _create_service(admin_client, client_id, title="Admin Will Patch This")
        svc_id = svc["id"]

        resp = await admin_client.patch(
            f"/api/services/{svc_id}",
            json={"title": "Admin Patched"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["title"] == "Admin Patched"


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}/state
# ---------------------------------------------------------------------------


class TestServiceStateTransition:
    async def test_valid_transition_returns_200_and_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """Valid state transition returns 200 + 'service_state_change' activity_log."""
        client_id = await _create_client(admin_client, "State Transition Corp")
        svc = await _create_service(admin_client, client_id, title="Transition Service")
        svc_id = svc["id"]

        resp = await admin_client.patch(
            f"/api/services/{svc_id}/state",
            json={"state": "running"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["state"] == "running"

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]
        assert "service_state_change" in kinds, f"Expected service_state_change in {kinds}"

    async def test_invalid_transition_returns_409_with_allowed(
        self, admin_client: httpx.AsyncClient
    ):
        """Invalid state transition → 409 with allowed_transitions in body."""
        client_id = await _create_client(admin_client, "Invalid State Corp")
        svc = await _create_service(admin_client, client_id, title="Bad Transition")
        svc_id = svc["id"]

        # scoping → completed is not a valid direct transition
        resp = await admin_client.patch(
            f"/api/services/{svc_id}/state",
            json={"state": "completed"},
        )

        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert body.get("error") == "invalid_transition"
        assert "allowed" in body
        assert isinstance(body["allowed"], list)
