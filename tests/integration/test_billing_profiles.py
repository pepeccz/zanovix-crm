"""
Integration tests — BillingProfile CRUD (PR-1 backend).

Coverage:
  POST /api/clients/{client_id}/billing-profiles
  GET  /api/clients/{client_id}/billing-profiles
  GET  /api/billing-profiles/{id}
  PATCH /api/billing-profiles/{id}
  DELETE /api/billing-profiles/{id}
  PATCH /api/billing-profiles/{id}/default
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from database.models.billing_profile import BillingProfile
from database.models.client import Client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_profile_payload(**overrides) -> dict:
    base = {
        "legal_name": "Empresa Test SL",
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


async def _seed_client(session_factory) -> uuid.UUID:
    async with session_factory() as session:
        client = Client(id=uuid.uuid4(), name="Test Client", stage="active")
        session.add(client)
        await session.commit()
        return client.id


async def _create_profile(
    http_client: httpx.AsyncClient,
    client_id: uuid.UUID,
    **payload_overrides,
) -> dict:
    payload = _valid_profile_payload(**payload_overrides)
    resp = await http_client.post(
        f"/api/clients/{client_id}/billing-profiles", json=payload
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Happy path — create + default logic
# ---------------------------------------------------------------------------


class TestBillingProfileCreate:
    async def test_create_first_profile_auto_default(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """First profile created for a client is always is_default=True."""
        client_id = await _seed_client(test_session_factory)
        data = await _create_profile(admin_client, client_id)

        assert data["is_default"] is True
        assert data["client_id"] == str(client_id)
        assert data["tax_id_type"] == "CIF"

    async def test_create_second_profile_not_default(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Second profile without is_default=True stays non-default."""
        client_id = await _seed_client(test_session_factory)
        await _create_profile(admin_client, client_id, tax_id="B1234567I")

        second = await _create_profile(
            admin_client,
            client_id,
            tax_id="A1234567I",
            tax_id_type="CIF",
            legal_name="Segunda Empresa SA",
        )
        assert second["is_default"] is False

    async def test_create_second_profile_with_default_demotes_others(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Requesting is_default=True on a second profile demotes the first."""
        client_id = await _seed_client(test_session_factory)
        first = await _create_profile(admin_client, client_id, tax_id="B1234567I")
        assert first["is_default"] is True

        second = await _create_profile(
            admin_client,
            client_id,
            tax_id="A1234567I",
            tax_id_type="CIF",
            legal_name="Segunda Empresa SA",
            is_default=True,
        )
        assert second["is_default"] is True

        # Re-fetch the first; it should no longer be default
        resp = await admin_client.get(f"/api/billing-profiles/{first['id']}")
        assert resp.status_code == 200
        assert resp.json()["is_default"] is False

    async def test_create_for_missing_client_returns_404(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Creating a profile for a non-existent client returns 404."""
        resp = await admin_client.post(
            f"/api/clients/{uuid.uuid4()}/billing-profiles",
            json=_valid_profile_payload(),
        )
        assert resp.status_code == 404

    async def test_list_orders_default_first_then_created_at(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """List returns default profile first, then others by created_at ASC."""
        client_id = await _seed_client(test_session_factory)
        first = await _create_profile(admin_client, client_id, tax_id="B1234567I")
        second = await _create_profile(
            admin_client,
            client_id,
            tax_id="A1234567I",
            tax_id_type="CIF",
            legal_name="Segunda SA",
        )

        resp = await admin_client.get(f"/api/clients/{client_id}/billing-profiles")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        # Default (first) must appear first
        assert items[0]["id"] == first["id"]
        assert items[0]["is_default"] is True
        assert items[1]["id"] == second["id"]


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------


class TestBillingProfileUpdate:
    async def test_patch_updates_partial_fields(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """PATCH with a subset of fields only changes those fields."""
        client_id = await _seed_client(test_session_factory)
        created = await _create_profile(admin_client, client_id)

        resp = await admin_client.patch(
            f"/api/billing-profiles/{created['id']}",
            json={"city": "Barcelona", "province": "Barcelona"},
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["city"] == "Barcelona"
        assert updated["province"] == "Barcelona"
        assert updated["legal_name"] == created["legal_name"]

    async def test_patch_change_tax_id_revalidates(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Changing tax_id with an invalid value returns 422."""
        client_id = await _seed_client(test_session_factory)
        created = await _create_profile(admin_client, client_id)

        resp = await admin_client.patch(
            f"/api/billing-profiles/{created['id']}",
            json={"tax_id": "INVALID123", "tax_id_type": "NIF"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Set default
# ---------------------------------------------------------------------------


class TestSetDefault:
    async def test_set_default_flips_only_within_client(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """PATCH /default promotes the given profile and demotes others in the same client."""
        client_id = await _seed_client(test_session_factory)
        first = await _create_profile(admin_client, client_id, tax_id="B1234567I")
        second = await _create_profile(
            admin_client,
            client_id,
            tax_id="A1234567I",
            tax_id_type="CIF",
            legal_name="Segunda SA",
        )

        assert first["is_default"] is True
        assert second["is_default"] is False

        resp = await admin_client.patch(f"/api/billing-profiles/{second['id']}/default")
        assert resp.status_code == 200
        assert resp.json()["is_default"] is True

        # First should now be non-default
        resp2 = await admin_client.get(f"/api/billing-profiles/{first['id']}")
        assert resp2.json()["is_default"] is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestBillingProfileDelete:
    async def test_delete_default_with_others_promotes_oldest(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Deleting the default profile auto-promotes the oldest sibling."""
        client_id = await _seed_client(test_session_factory)
        first = await _create_profile(admin_client, client_id, tax_id="B1234567I")
        second = await _create_profile(
            admin_client,
            client_id,
            tax_id="A1234567I",
            tax_id_type="CIF",
            legal_name="Segunda SA",
        )

        # Delete the default (first)
        resp = await admin_client.delete(f"/api/billing-profiles/{first['id']}")
        assert resp.status_code == 204

        # Second should now be default
        resp2 = await admin_client.get(f"/api/billing-profiles/{second['id']}")
        assert resp2.json()["is_default"] is True

    async def test_cascade_delete_on_client_delete(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Deleting a client cascades and removes all its billing profiles (ON DELETE CASCADE)."""
        client_id = await _seed_client(test_session_factory)
        profile = await _create_profile(admin_client, client_id)

        # Delete client directly via DB (no client DELETE endpoint exists yet).
        # The FK ON DELETE CASCADE should remove the billing profile automatically.
        async with test_session_factory() as session:
            from database.models.client import Client
            client = (await session.execute(
                select(Client).where(Client.id == client_id)
            )).scalar_one()
            await session.delete(client)
            await session.commit()

        # Profile should no longer exist
        async with test_session_factory() as session:
            stmt = select(BillingProfile).where(
                BillingProfile.id == uuid.UUID(profile["id"])
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            assert row is None


# ---------------------------------------------------------------------------
# Error paths (F.3)
# ---------------------------------------------------------------------------


class TestBillingProfileErrors:
    async def test_create_invalid_nif_returns_422(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Creating a profile with an invalid NIF format returns 422."""
        client_id = await _seed_client(test_session_factory)
        payload = _valid_profile_payload(tax_id="12345678A", tax_id_type="NIF")
        resp = await admin_client.post(
            f"/api/clients/{client_id}/billing-profiles", json=payload
        )
        assert resp.status_code == 422

    async def test_create_duplicate_tax_id_per_client_returns_409(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Creating two profiles with the same tax_id for the same client → 409."""
        client_id = await _seed_client(test_session_factory)
        await _create_profile(admin_client, client_id, tax_id="B1234567I")

        resp = await admin_client.post(
            f"/api/clients/{client_id}/billing-profiles",
            json=_valid_profile_payload(tax_id="B1234567I", legal_name="Otra Empresa"),
        )
        assert resp.status_code == 409
        assert resp.json()["error"] == "duplicate_tax_id"

    async def test_delete_only_default_returns_409(
        self,
        admin_client: httpx.AsyncClient,
        test_session_factory,
    ) -> None:
        """Deleting the only billing profile returns 409."""
        client_id = await _seed_client(test_session_factory)
        profile = await _create_profile(admin_client, client_id)

        resp = await admin_client.delete(f"/api/billing-profiles/{profile['id']}")
        assert resp.status_code == 409
        assert resp.json()["error"] == "cannot_delete_only_default"

    async def test_client_portal_user_gets_403(
        self,
        test_session_factory,
        client_user,
    ) -> None:
        """Client portal users cannot access billing profile endpoints — 403."""
        from tests.integration._app_factory import make_role_app
        import httpx

        portal_app = make_role_app(client_user)
        transport = httpx.ASGITransport(app=portal_app)

        client_id = await _seed_client(test_session_factory)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(f"/api/clients/{client_id}/billing-profiles")
            assert resp.status_code == 403
