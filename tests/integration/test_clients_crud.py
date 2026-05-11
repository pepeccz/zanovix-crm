"""
Integration tests — Clients CRUD (TASK-31).

Coverage:
- POST /api/clients:
    - admin → 201 + correct shape (ClientRead)
    - consultor → 403
- GET /api/clients:
    - pagination shape {items, total, limit, offset}
    - stage filter
    - q (ILIKE name) filter
    - limit > 200 → 400 with error shape
- GET /api/clients/{id}:
    - ClientDetailResponse with contacts / services / recent_activity
    - 404 for missing client
- PATCH /api/clients/{id}:
    - admin updates metadata → 200 + updated values
- PATCH /api/clients/{id}/stage:
    - valid transition → 200
    - invalid transition → 409 + allowed_transitions in body
"""

from __future__ import annotations

import uuid

import httpx
import pytest


# ---------------------------------------------------------------------------
# POST /api/clients
# ---------------------------------------------------------------------------


class TestCreateClient:
    async def test_admin_creates_client_201(
        self, admin_client: httpx.AsyncClient, admin_user
    ):
        """POST as admin returns 201 and correct ClientRead shape."""
        payload = {"name": "Alpha Corp", "sector": "fintech", "stage": "lead"}
        resp = await admin_client.post("/api/clients", json=payload)

        assert resp.status_code == 201, resp.text
        body = resp.json()

        # Required fields present
        assert body["name"] == "Alpha Corp"
        assert body["sector"] == "fintech"
        assert body["stage"] == "lead"
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        assert "entered_at" in body
        # Nullable fields default to None
        assert body["region"] is None
        assert body["size"] is None
        assert body["mrr_cents"] is None
        assert body["lifetime_value_cents"] is None

    async def test_consultor_cannot_create_client_403(
        self, consultor_client: httpx.AsyncClient
    ):
        """POST as consultor returns 403 (REQ-14-A)."""
        payload = {"name": "Should Fail"}
        resp = await consultor_client.post("/api/clients", json=payload)

        assert resp.status_code == 403, resp.text

    async def test_create_with_all_fields(
        self, admin_client: httpx.AsyncClient, admin_user
    ):
        """Admin can supply all optional fields on create."""
        payload = {
            "name": "Beta Industries",
            "sector": "health",
            "size": "51-200",
            "region": "EMEA",
            "mrr_cents": 50000,
            "stage": "discovery_scheduled",
            "owner_id": str(admin_user.id),
        }
        resp = await admin_client.post("/api/clients", json=payload)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["sector"] == "health"
        assert body["size"] == "51-200"
        assert body["region"] == "EMEA"
        assert body["mrr_cents"] == 50000
        assert body["stage"] == "discovery_scheduled"
        assert body["owner_id"] == str(admin_user.id)


# ---------------------------------------------------------------------------
# GET /api/clients (list)
# ---------------------------------------------------------------------------


class TestListClients:
    async def _create_client(
        self, client: httpx.AsyncClient, name: str, stage: str = "lead"
    ) -> dict:
        resp = await client.post(
            "/api/clients", json={"name": name, "stage": stage}
        )
        assert resp.status_code == 201
        return resp.json()

    async def test_list_returns_pagination_shape(self, admin_client: httpx.AsyncClient):
        """GET /api/clients returns {items, total, limit, offset}."""
        await self._create_client(admin_client, "Pagination Corp")

        resp = await admin_client.get("/api/clients")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert isinstance(body["items"], list)
        assert body["total"] >= 1
        assert body["limit"] == 50  # default
        assert body["offset"] == 0  # default

    async def test_stage_filter(self, admin_client: httpx.AsyncClient):
        """GET /api/clients?stage=lead returns only lead-stage clients."""
        await self._create_client(admin_client, "Lead Client A", stage="lead")
        await self._create_client(admin_client, "Active Client A", stage="lead")

        # Transition one to discovery_scheduled
        list_resp = await admin_client.get("/api/clients")
        items = list_resp.json()["items"]
        first_id = items[0]["id"]
        await admin_client.patch(
            f"/api/clients/{first_id}/stage",
            json={"stage": "discovery_scheduled"},
        )

        resp_lead = await admin_client.get("/api/clients?stage=lead")
        resp_disc = await admin_client.get("/api/clients?stage=discovery_scheduled")

        assert resp_lead.status_code == 200
        assert resp_disc.status_code == 200
        lead_items = resp_lead.json()["items"]
        disc_items = resp_disc.json()["items"]
        assert all(c["stage"] == "lead" for c in lead_items)
        assert all(c["stage"] == "discovery_scheduled" for c in disc_items)

    async def test_q_filter_ilike(self, admin_client: httpx.AsyncClient):
        """GET /api/clients?q=unique returns only clients whose name matches."""
        await self._create_client(admin_client, "UniqueXYZ Corp")
        await self._create_client(admin_client, "AnotherCorp")

        resp = await admin_client.get("/api/clients?q=uniquexyz")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all("UniqueXYZ" in c["name"] for c in body["items"])

    async def test_limit_exceeds_max_returns_400(self, admin_client: httpx.AsyncClient):
        """GET /api/clients?limit=300 → 400 with error body."""
        resp = await admin_client.get("/api/clients?limit=300")

        assert resp.status_code == 400, resp.text
        body = resp.json()
        # FastAPI wraps HTTPException detail under 'detail' key
        assert body.get("detail", {}).get("error") == "limit_exceeds_max"
        assert body.get("detail", {}).get("max") == 200

    async def test_pagination_offset(self, admin_client: httpx.AsyncClient):
        """Offset pagination returns correct slice."""
        for i in range(3):
            await self._create_client(admin_client, f"Paginated Client {i}")

        resp_all = await admin_client.get("/api/clients?limit=2&offset=0")
        resp_offset = await admin_client.get("/api/clients?limit=2&offset=2")

        assert resp_all.status_code == 200
        assert resp_offset.status_code == 200
        all_items = resp_all.json()["items"]
        offset_items = resp_offset.json()["items"]
        assert len(all_items) == 2
        # Offset must return different items (or empty if < 3 total)
        if offset_items:
            assert offset_items[0]["id"] != all_items[0]["id"]


# ---------------------------------------------------------------------------
# GET /api/clients/{id}
# ---------------------------------------------------------------------------


class TestGetClientDetail:
    async def test_detail_returns_correct_shape(self, admin_client: httpx.AsyncClient):
        """GET /api/clients/{id} returns ClientDetailResponse shape."""
        create_resp = await admin_client.post(
            "/api/clients", json={"name": "Detail Corp"}
        )
        assert create_resp.status_code == 201
        client_id = create_resp.json()["id"]

        resp = await admin_client.get(f"/api/clients/{client_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()

        # ClientDetailResponse fields
        assert body["id"] == client_id
        assert body["name"] == "Detail Corp"
        assert "contacts" in body
        assert "services" in body
        assert "recent_activity" in body
        assert isinstance(body["contacts"], list)
        assert isinstance(body["services"], list)
        assert isinstance(body["recent_activity"], list)

    async def test_detail_includes_recent_activity(self, admin_client: httpx.AsyncClient):
        """Detail response includes activity_log entries (at least the creation entry)."""
        create_resp = await admin_client.post(
            "/api/clients", json={"name": "Activity Corp"}
        )
        client_id = create_resp.json()["id"]

        resp = await admin_client.get(f"/api/clients/{client_id}")
        body = resp.json()

        # Client creation writes a stage_change activity log entry
        assert len(body["recent_activity"]) >= 1
        kinds = [a["kind"] for a in body["recent_activity"]]
        assert "stage_change" in kinds

    async def test_detail_404_for_missing_client(self, admin_client: httpx.AsyncClient):
        """GET /api/clients/{nonexistent} → 404."""
        resp = await admin_client.get(f"/api/clients/{uuid.uuid4()}")
        assert resp.status_code == 404, resp.text

    async def test_detail_embeds_contacts(self, admin_client: httpx.AsyncClient):
        """Contacts added to a client appear in the detail response."""
        create_resp = await admin_client.post(
            "/api/clients", json={"name": "Contact Embed Corp"}
        )
        client_id = create_resp.json()["id"]

        # Add a contact
        await admin_client.post(
            f"/api/clients/{client_id}/contacts",
            json={"client_id": client_id, "name": "Jane Doe", "email": "jane@example.com"},
        )

        resp = await admin_client.get(f"/api/clients/{client_id}")
        body = resp.json()

        assert len(body["contacts"]) == 1
        assert body["contacts"][0]["name"] == "Jane Doe"

    async def test_detail_embeds_services(self, admin_client: httpx.AsyncClient):
        """Services created under a client appear as stubs in the detail response."""
        create_resp = await admin_client.post(
            "/api/clients", json={"name": "Service Embed Corp"}
        )
        client_id = create_resp.json()["id"]

        await admin_client.post(
            f"/api/clients/{client_id}/services",
            json={"type": "assessment", "title": "Q1 Assessment", "client_id": str(client_id)},
        )

        resp = await admin_client.get(f"/api/clients/{client_id}")
        body = resp.json()

        assert len(body["services"]) == 1
        stub = body["services"][0]
        assert stub["title"] == "Q1 Assessment"
        assert stub["type"] == "assessment"
        # ServiceStub has limited fields (not full ServiceRead)
        assert "id" in stub
        assert "state" in stub


# ---------------------------------------------------------------------------
# PATCH /api/clients/{id}
# ---------------------------------------------------------------------------


class TestUpdateClient:
    async def test_admin_patches_metadata(self, admin_client: httpx.AsyncClient):
        """PATCH /api/clients/{id} updates non-stage fields."""
        create_resp = await admin_client.post(
            "/api/clients", json={"name": "Old Name Corp"}
        )
        client_id = create_resp.json()["id"]

        resp = await admin_client.patch(
            f"/api/clients/{client_id}",
            json={"name": "New Name Corp", "sector": "manufacturing", "mrr_cents": 10000},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "New Name Corp"
        assert body["sector"] == "manufacturing"
        assert body["mrr_cents"] == 10000

    async def test_patch_404_for_missing_client(self, admin_client: httpx.AsyncClient):
        """PATCH on a nonexistent client → 404."""
        resp = await admin_client.patch(
            f"/api/clients/{uuid.uuid4()}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# PATCH /api/clients/{id}/stage
# ---------------------------------------------------------------------------


class TestClientStageTransition:
    async def _create_client(self, client: httpx.AsyncClient, stage: str = "lead") -> str:
        resp = await client.post(
            "/api/clients", json={"name": "Stage Corp", "stage": stage}
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_valid_transition_returns_200(self, admin_client: httpx.AsyncClient):
        """Valid stage transition returns 200 and updated stage."""
        client_id = await self._create_client(admin_client, stage="lead")

        resp = await admin_client.patch(
            f"/api/clients/{client_id}/stage",
            json={"stage": "discovery_scheduled"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] == "discovery_scheduled"

    async def test_invalid_transition_returns_409_with_allowed(
        self, admin_client: httpx.AsyncClient
    ):
        """Invalid transition returns 409 with allowed_transitions in body."""
        client_id = await self._create_client(admin_client, stage="lead")

        resp = await admin_client.patch(
            f"/api/clients/{client_id}/stage",
            json={"stage": "active"},  # lead → active is not a valid transition
        )

        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert "error" in body
        assert body["error"] == "invalid_transition"
        assert "allowed" in body
        assert isinstance(body["allowed"], list)

    async def test_any_stage_to_lost_is_valid(self, admin_client: httpx.AsyncClient):
        """Any non-terminal stage can transition to 'lost' (REQ-8-C)."""
        client_id = await self._create_client(admin_client, stage="lead")

        resp = await admin_client.patch(
            f"/api/clients/{client_id}/stage",
            json={"stage": "lost"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] == "lost"
