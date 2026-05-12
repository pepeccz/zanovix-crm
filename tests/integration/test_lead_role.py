"""
Integration tests — Lead.role field (R1.1–R1.4).

Coverage:
  - Creating a lead with role stores it correctly.
  - Creating a lead without role defaults to null.
  - Updating a lead's role via PATCH /api/leads/{id}.
  - role > 100 chars returns 422 (max_length enforcement).
"""

from __future__ import annotations

import uuid

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lead_payload(**overrides) -> dict:
    """Minimal valid lead payload."""
    base = {
        "name": "Test Lead",
        "email": f"lead-{uuid.uuid4().hex[:6]}@example.com",
        "vertical": "general",
        "channel": "web_form",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLeadRole:
    async def test_create_lead_with_role(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """POST /api/leads with role stores and returns the role."""
        payload = _lead_payload(role="CTO")
        resp = await admin_client.post("/api/leads", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["role"] == "CTO"

    async def test_create_lead_without_role_defaults_null(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """POST /api/leads without role → role is null in response."""
        payload = _lead_payload()
        resp = await admin_client.post("/api/leads", json=payload)
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] is None

    async def test_update_lead_role(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """PATCH /api/leads/{id} with role updates the field."""
        # Create lead first
        create_resp = await admin_client.post("/api/leads", json=_lead_payload())
        assert create_resp.status_code == 201
        lead_id = create_resp.json()["id"]

        # Update role
        patch_resp = await admin_client.patch(
            f"/api/leads/{lead_id}",
            json={"role": "Director Técnico"},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["role"] == "Director Técnico"

    async def test_role_max_length_422(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """role longer than 100 chars returns 422."""
        payload = _lead_payload(role="A" * 101)
        resp = await admin_client.post("/api/leads", json=payload)
        assert resp.status_code == 422, resp.text
