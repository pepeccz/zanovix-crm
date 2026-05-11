"""
Integration tests — Lead → Client Conversion (TASK-35).

Coverage (REQ-13 scenarios):
- POST /api/leads/{id}/convert:
    - Happy path (qualified lead) → 201 + ClientRead
      client.name defaults from lead.company
      lead.status = "converted"
      lead.converted_client_id set
      activity_log entry "lead_converted" written
    - Body field overrides take precedence over lead defaults
- Already converted lead → 409 with error=already_converted + client_id
- Non-qualified lead → 422 with error=lead_not_qualified
- Consultor cannot convert → 403 (REQ-14: lead.convert = admin + comercial only)
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from database.models.activity_log import ActivityLog
from database.models.lead import Lead


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_lead(
    session_factory,
    owner_id: uuid.UUID,
    status: str = "qualified",
    name: str = "John Smith",
    email_suffix: str = "",
    company: str = "ACME Inc",
) -> uuid.UUID:
    """
    Insert a Lead directly into the DB (bypassing the rate-limited public endpoint)
    so tests don't need to worry about rate limits or a public-facing route.
    """
    async with session_factory() as session:
        lead = Lead(
            id=uuid.uuid4(),
            name=name,
            email=f"john{email_suffix}@acme.test",
            company=company,
            vertical="general",
            channel="web_form",
            status=status,
            owner_id=owner_id,
            raw_payload={},
        )
        session.add(lead)
        await session.commit()
        return lead.id


async def _get_lead(session_factory, lead_id: uuid.UUID) -> Lead:
    async with session_factory() as session:
        stmt = select(Lead).where(Lead.id == lead_id)
        return (await session.execute(stmt)).scalar_one()


async def _count_activity(session_factory, client_id: uuid.UUID, kind: str) -> int:
    async with session_factory() as session:
        stmt = select(ActivityLog).where(
            ActivityLog.client_id == client_id,
            ActivityLog.kind == kind,
        )
        rows = (await session.execute(stmt)).scalars().all()
        return len(rows)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestConvertLeadHappyPath:
    async def test_qualified_lead_converts_201(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """POST /api/leads/{id}/convert with qualified lead → 201 + ClientRead."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            company="ACME Corp",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})

        assert resp.status_code == 201, resp.text
        body = resp.json()
        # Client shape
        assert "id" in body
        assert "name" in body
        assert "stage" in body
        assert "created_at" in body

    async def test_client_name_defaults_from_lead_company(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """When body.name is absent, client.name defaults to lead.company (REQ-13-A)."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            company="DefaultCompany SA",
            email_suffix="_default",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})

        assert resp.status_code == 201
        assert resp.json()["name"] == "DefaultCompany SA"

    async def test_lead_status_set_to_converted(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """After conversion, lead.status == 'converted' (REQ-13-A)."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            email_suffix="_status",
        )

        await admin_client.post(f"/api/leads/{lead_id}/convert", json={})

        lead = await _get_lead(test_session_factory, lead_id)
        assert lead.status == "converted"

    async def test_lead_converted_client_id_set(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """After conversion, lead.converted_client_id points to the new client."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            email_suffix="_link",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        client_id = resp.json()["id"]

        lead = await _get_lead(test_session_factory, lead_id)
        assert lead.converted_client_id is not None
        assert str(lead.converted_client_id) == client_id

    async def test_activity_log_lead_converted_written(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """Conversion writes a 'lead_converted' activity_log entry on the new client."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            email_suffix="_activity",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        client_id = resp.json()["id"]

        count = await _count_activity(
            test_session_factory, uuid.UUID(client_id), "lead_converted"
        )
        assert count == 1, f"Expected 1 lead_converted activity, got {count}"

    async def test_body_overrides_take_precedence(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """Body fields override lead defaults (REQ-13-D)."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            company="Original Corp",
            email_suffix="_override",
        )

        resp = await admin_client.post(
            f"/api/leads/{lead_id}/convert",
            json={"name": "Override Name", "sector": "health", "mrr_cents": 99000},
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Override Name"
        assert body["sector"] == "health"
        assert body["mrr_cents"] == 99000


# ---------------------------------------------------------------------------
# Error scenarios
# ---------------------------------------------------------------------------


class TestConvertLeadErrors:
    async def test_already_converted_returns_409(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """Converting a lead twice → 409 with error=already_converted + client_id (REQ-13-C)."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            email_suffix="_double",
        )

        # First conversion succeeds
        first = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        assert first.status_code == 201

        # Second conversion must fail
        second = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})

        assert second.status_code == 409, second.text
        body = second.json()
        assert body.get("error") == "already_converted"
        assert "client_id" in body
        assert body["client_id"] == first.json()["id"]

    async def test_non_qualified_lead_returns_422(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """Converting a non-qualified lead → 422 with error=lead_not_qualified (REQ-13-B)."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="new",  # not qualified
            email_suffix="_notqualified",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})

        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body.get("error") == "lead_not_qualified"

    async def test_consultor_cannot_convert_403(
        self,
        consultor_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ):
        """Consultor role is not allowed to convert leads → 403."""
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            status="qualified",
            email_suffix="_consultor403",
        )

        resp = await consultor_client.post(f"/api/leads/{lead_id}/convert", json={})

        assert resp.status_code == 403, resp.text

    async def test_convert_nonexistent_lead_returns_404(
        self,
        admin_client: httpx.AsyncClient,
    ):
        """Converting a nonexistent lead → 404."""
        resp = await admin_client.post(f"/api/leads/{uuid.uuid4()}/convert", json={})
        assert resp.status_code == 404, resp.text
