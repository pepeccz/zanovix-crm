"""
Integration tests — Lead conversion with BillingProfile and auto-Contact (Option B).

Covers design §5 (convert_from_lead 7-step flow):
  - Client + Contact + BillingProfile created atomically.
  - lead.role propagated verbatim to the primary Contact.
  - Invalid billing payload rolls back entire transaction.
  - Backward compatibility: conversion without billing_profile works unchanged.

New tests per tasks F.4 and F.5.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from database.models.client import Client
from database.models.contact import Contact
from database.models.lead import Lead


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_lead(
    session_factory,
    owner_id: uuid.UUID,
    status: str = "qualified",
    name: str = "Ana García",
    email: str = "ana@empresa.test",
    phone: str | None = "+34 600 000 001",
    company: str | None = "EmpresaTest SL",
    role: str | None = None,
) -> uuid.UUID:
    async with session_factory() as session:
        lead = Lead(
            id=uuid.uuid4(),
            name=name,
            email=email,
            phone=phone,
            company=company,
            vertical="general",
            channel="web_form",
            status=status,
            owner_id=owner_id,
            raw_payload={},
            role=role,
        )
        session.add(lead)
        await session.commit()
        return lead.id


def _valid_billing_payload(**overrides) -> dict:
    base = {
        "legal_name": "EmpresaTest SL",
        "tax_id": "B1234567I",
        "tax_id_type": "CIF",
        "tax_regime": "general",
        "address_line1": "Calle Mayor 1",
        "city": "Madrid",
        "province": "Madrid",
        "postal_code": "28001",
        "country": "ES",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# F.4 — conversion with BillingProfile
# ---------------------------------------------------------------------------


class TestConvertWithBillingProfile:
    async def test_convert_with_billing_profile_atomic_success(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ) -> None:
        """
        Conversion with billing_profile creates client + contact + profile atomically.
        The billing profile must have is_default=True.
        """
        lead_id = await _seed_lead(test_session_factory, owner_id=admin_user.id)

        resp = await admin_client.post(
            f"/api/leads/{lead_id}/convert",
            json={"billing_profile": _valid_billing_payload()},
        )
        assert resp.status_code == 201, resp.text
        client_data = resp.json()
        client_id = uuid.UUID(client_data["id"])

        # Verify billing profile was created and is_default
        async with test_session_factory() as session:
            from database.models.billing_profile import BillingProfile
            stmt = select(BillingProfile).where(BillingProfile.client_id == client_id)
            profile = (await session.execute(stmt)).scalar_one_or_none()
            assert profile is not None
            assert profile.is_default is True
            assert profile.tax_id == "B1234567I"

    async def test_convert_with_invalid_billing_rolls_back_client_creation(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ) -> None:
        """
        Conversion with invalid billing_profile payload returns 422 and no client
        row is persisted (Pydantic validation rejects before DB write).
        """
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            email="rollback@test.test",
        )

        resp = await admin_client.post(
            f"/api/leads/{lead_id}/convert",
            json={
                "billing_profile": _valid_billing_payload(
                    tax_id="INVALIDO",  # bad format for CIF
                )
            },
        )
        assert resp.status_code == 422, resp.text

        # Lead must remain unconverted
        async with test_session_factory() as session:
            stmt = select(Lead).where(Lead.id == lead_id)
            lead = (await session.execute(stmt)).scalar_one()
            assert lead.status == "qualified"
            assert lead.converted_client_id is None

    async def test_convert_without_billing_profile_unchanged_behavior(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ) -> None:
        """
        Backward compatibility: conversion without billing_profile still succeeds,
        creates client + primary contact, no billing profile row.
        """
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            email="notnew@compat.test",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        assert resp.status_code == 201, resp.text
        client_id = uuid.UUID(resp.json()["id"])

        async with test_session_factory() as session:
            from database.models.billing_profile import BillingProfile
            stmt = select(BillingProfile).where(BillingProfile.client_id == client_id)
            profiles = (await session.execute(stmt)).scalars().all()
            assert len(profiles) == 0


# ---------------------------------------------------------------------------
# F.5 — auto-Contact creation with role propagation
# ---------------------------------------------------------------------------


class TestConvertAutoContact:
    async def test_convert_from_lead_auto_creates_primary_contact_with_role(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ) -> None:
        """
        After conversion, the new client has exactly one Contact with:
          - name == lead.name
          - email == lead.email
          - phone == lead.phone
          - role == lead.role
          - is_primary == True
        """
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            name="María López",
            email="maria@empresa.test",
            phone="+34 600 000 002",
            role="Directora Comercial",
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        assert resp.status_code == 201, resp.text
        client_id = uuid.UUID(resp.json()["id"])

        async with test_session_factory() as session:
            stmt = select(Contact).where(Contact.client_id == client_id)
            contacts = (await session.execute(stmt)).scalars().all()
            assert len(contacts) == 1
            c = contacts[0]
            assert c.name == "María López"
            assert c.email == "maria@empresa.test"
            assert c.phone == "+34 600 000 002"
            assert c.role == "Directora Comercial"
            assert c.is_primary is True

    async def test_convert_from_lead_with_null_role_yields_contact_with_null_role(
        self,
        admin_client: httpx.AsyncClient,
        admin_user,
        test_session_factory,
    ) -> None:
        """
        When lead.role IS NULL, the resulting Contact also has role IS NULL.
        Null email/phone are also copied verbatim (not defaulted).
        """
        lead_id = await _seed_lead(
            test_session_factory,
            owner_id=admin_user.id,
            name="Pedro Sin Rol",
            email="pedro@empresa.test",
            phone=None,
            role=None,
        )

        resp = await admin_client.post(f"/api/leads/{lead_id}/convert", json={})
        assert resp.status_code == 201, resp.text
        client_id = uuid.UUID(resp.json()["id"])

        async with test_session_factory() as session:
            stmt = select(Contact).where(Contact.client_id == client_id)
            contacts = (await session.execute(stmt)).scalars().all()
            assert len(contacts) == 1
            c = contacts[0]
            assert c.name == "Pedro Sin Rol"
            assert c.email == "pedro@empresa.test"
            assert c.phone is None
            assert c.role is None
            assert c.is_primary is True
