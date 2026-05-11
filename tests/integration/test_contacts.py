"""
Integration tests — Contacts CRUD (TASK-34).

Coverage:
- POST /api/clients/{id}/contacts:
    - 201 + ContactRead shape
    - activity_log entry "contact_added" on parent client
- GET /api/clients/{id}/contacts:
    - returns list of ContactRead
- PATCH /api/clients/{id}/contacts/{contact_id}:
    - 200 + activity_log "contact_updated"
- DELETE /api/clients/{id}/contacts/{contact_id}:
    - admin → 204
    - comercial → 403
"""

from __future__ import annotations

import uuid

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(client: httpx.AsyncClient, name: str = "Contact Parent Corp") -> str:
    resp = await client.post("/api/clients", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_contact(
    client: httpx.AsyncClient,
    client_id: str,
    name: str = "Jane Doe",
    email: str = "jane@example.com",
) -> dict:
    resp = await client.post(
        f"/api/clients/{client_id}/contacts",
        json={"name": name, "email": email, "client_id": client_id},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/clients/{id}/contacts
# ---------------------------------------------------------------------------


class TestCreateContact:
    async def test_create_returns_201_and_shape(self, admin_client: httpx.AsyncClient):
        """POST contact returns 201 + ContactRead shape."""
        client_id = await _create_client(admin_client)

        resp = await admin_client.post(
            f"/api/clients/{client_id}/contacts",
            json={
                "client_id": client_id,
                "name": "Alice Smith",
                "role": "CTO",
                "email": "alice@example.com",
                "phone": "+34600000001",
                "is_primary": True,
            },
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Alice Smith"
        assert body["role"] == "CTO"
        assert body["email"] == "alice@example.com"
        assert body["phone"] == "+34600000001"
        assert body["is_primary"] is True
        assert "id" in body
        assert "client_id" in body
        assert body["client_id"] == client_id

    async def test_create_writes_contact_added_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """Creating a contact writes a 'contact_added' activity_log entry."""
        client_id = await _create_client(admin_client, "Activity Track Corp")
        await _create_contact(admin_client, client_id, "Bob Jones")

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]

        assert "contact_added" in kinds, f"Expected contact_added in {kinds}"

    async def test_consultor_cannot_create_contact_403(
        self, consultor_client: httpx.AsyncClient, admin_client: httpx.AsyncClient
    ):
        """Consultor cannot create contacts (403)."""
        client_id = await _create_client(admin_client, "Consultor Block Corp")

        resp = await consultor_client.post(
            f"/api/clients/{client_id}/contacts",
            json={"name": "Unauthorized Contact", "client_id": client_id},
        )

        assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# GET /api/clients/{id}/contacts
# ---------------------------------------------------------------------------


class TestListContacts:
    async def test_list_returns_contacts(self, admin_client: httpx.AsyncClient):
        """GET contacts under client returns the full list."""
        client_id = await _create_client(admin_client, "List Contacts Corp")
        await _create_contact(admin_client, client_id, "Contact One", "c1@example.com")
        await _create_contact(admin_client, client_id, "Contact Two", "c2@example.com")

        resp = await admin_client.get(f"/api/clients/{client_id}/contacts")

        assert resp.status_code == 200, resp.text
        contacts = resp.json()
        assert isinstance(contacts, list)
        assert len(contacts) == 2
        names = {c["name"] for c in contacts}
        assert names == {"Contact One", "Contact Two"}

    async def test_list_empty_for_new_client(self, admin_client: httpx.AsyncClient):
        """A freshly created client has no contacts."""
        client_id = await _create_client(admin_client, "Empty Contacts Corp")

        resp = await admin_client.get(f"/api/clients/{client_id}/contacts")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# PATCH /api/clients/{id}/contacts/{contact_id}
# ---------------------------------------------------------------------------


class TestUpdateContact:
    async def test_patch_updates_contact(self, admin_client: httpx.AsyncClient):
        """PATCH contact → 200 + updated fields."""
        client_id = await _create_client(admin_client, "Update Contact Corp")
        contact = await _create_contact(admin_client, client_id, "Original Name")
        contact_id = contact["id"]

        resp = await admin_client.patch(
            f"/api/clients/{client_id}/contacts/{contact_id}",
            json={"name": "Updated Name", "role": "CEO"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "Updated Name"
        assert body["role"] == "CEO"
        assert body["id"] == contact_id

    async def test_patch_writes_contact_updated_activity(
        self, admin_client: httpx.AsyncClient
    ):
        """Updating a contact writes a 'contact_updated' activity_log entry."""
        client_id = await _create_client(admin_client, "Activity Update Corp")
        contact = await _create_contact(admin_client, client_id, "Track Me")
        contact_id = contact["id"]

        await admin_client.patch(
            f"/api/clients/{client_id}/contacts/{contact_id}",
            json={"role": "VP Engineering"},
        )

        detail_resp = await admin_client.get(f"/api/clients/{client_id}")
        activity = detail_resp.json()["recent_activity"]
        kinds = [a["kind"] for a in activity]

        assert "contact_updated" in kinds, f"Expected contact_updated in {kinds}"

    async def test_patch_404_for_missing_contact(self, admin_client: httpx.AsyncClient):
        """PATCH nonexistent contact → 404."""
        client_id = await _create_client(admin_client, "Ghost Contact Corp")
        nonexistent_id = str(uuid.uuid4())

        resp = await admin_client.patch(
            f"/api/clients/{client_id}/contacts/{nonexistent_id}",
            json={"name": "Ghost"},
        )

        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# DELETE /api/clients/{id}/contacts/{contact_id}
# ---------------------------------------------------------------------------


class TestDeleteContact:
    async def test_admin_deletes_contact_204(self, admin_client: httpx.AsyncClient):
        """Admin can delete a contact → 204 No Content."""
        client_id = await _create_client(admin_client, "Delete Contact Corp")
        contact = await _create_contact(admin_client, client_id, "To Be Deleted")
        contact_id = contact["id"]

        resp = await admin_client.delete(
            f"/api/clients/{client_id}/contacts/{contact_id}"
        )

        assert resp.status_code == 204, resp.text
        # Verify gone
        list_resp = await admin_client.get(f"/api/clients/{client_id}/contacts")
        assert list_resp.json() == []

    async def test_comercial_cannot_delete_contact_403(
        self,
        comercial_client: httpx.AsyncClient,
        admin_client: httpx.AsyncClient,
    ):
        """Comercial cannot delete a contact (admin-only) → 403."""
        client_id = await _create_client(admin_client, "RBAC Delete Corp")
        contact = await _create_contact(admin_client, client_id, "Protected Contact")
        contact_id = contact["id"]

        resp = await comercial_client.delete(
            f"/api/clients/{client_id}/contacts/{contact_id}"
        )

        assert resp.status_code == 403, resp.text
