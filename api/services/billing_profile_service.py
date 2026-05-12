"""
BillingProfile service — business logic for fiscal identity profiles attached to a Client.

Design principles:
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- services flush; routes commit.
- Domain exceptions are raised here and mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.billing_profile import BillingProfileCreate, BillingProfileUpdate
from api.services.exceptions import (
    BillingProfileNotFoundError,
    CannotDeleteOnlyDefaultError,
    ClientNotFoundError,
    DuplicateTaxIdError,
)
from database.models.billing_profile import BillingProfile
from database.models.client import Client

logger = logging.getLogger(__name__)


class BillingProfileService:
    """
    Service layer for the BillingProfile aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Internal helpers ───────────────────────────────────────────────────

    async def _assert_client_exists(self, client_id: uuid.UUID) -> None:
        stmt = select(Client).where(Client.id == client_id)
        client = (await self.session.execute(stmt)).scalar_one_or_none()
        if client is None:
            raise ClientNotFoundError(client_id)

    async def _assert_unique_tax_id(
        self, client_id: uuid.UUID, tax_id: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        stmt = select(BillingProfile).where(
            BillingProfile.client_id == client_id,
            BillingProfile.tax_id == tax_id,
        )
        if exclude_id is not None:
            stmt = stmt.where(BillingProfile.id != exclude_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise DuplicateTaxIdError(client_id, tax_id)

    async def _count_for_client(self, client_id: uuid.UUID) -> int:
        stmt = select(func.count(BillingProfile.id)).where(
            BillingProfile.client_id == client_id
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def _load(self, profile_id: uuid.UUID) -> BillingProfile:
        stmt = select(BillingProfile).where(BillingProfile.id == profile_id)
        profile = (await self.session.execute(stmt)).scalar_one_or_none()
        if profile is None:
            raise BillingProfileNotFoundError(profile_id)
        return profile

    # ─── Write ──────────────────────────────────────────────────────────────

    async def create_for_client(
        self, client_id: uuid.UUID, payload: BillingProfileCreate
    ) -> BillingProfile:
        """
        Create a new BillingProfile for the given client.

        Business rules:
          - Client must exist → ClientNotFoundError.
          - tax_id must be unique per client → DuplicateTaxIdError (409).
          - First profile on a client is always forced to is_default=True.
          - If payload.is_default=True and there are existing profiles, demote them.
        """
        await self._assert_client_exists(client_id)
        await self._assert_unique_tax_id(client_id, payload.tax_id)

        count = await self._count_for_client(client_id)
        force_default = count == 0

        if force_default:
            is_default = True
        elif payload.is_default:
            # Demote all existing defaults for this client
            await self.session.execute(
                update(BillingProfile)
                .where(BillingProfile.client_id == client_id)
                .values(is_default=False)
            )
            is_default = True
        else:
            is_default = False

        profile = BillingProfile(
            client_id=client_id,
            legal_name=payload.legal_name,
            tax_id=payload.tax_id,
            tax_id_type=payload.tax_id_type,
            tax_regime=payload.tax_regime,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            province=payload.province,
            postal_code=payload.postal_code,
            country=payload.country,
            billing_email=payload.billing_email,
            is_default=is_default,
        )
        self.session.add(profile)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_billing_profile_client_tax_id" in str(exc.orig):
                await self.session.rollback()
                raise DuplicateTaxIdError(client_id, payload.tax_id) from exc
            raise
        await self.session.refresh(profile)
        logger.info(
            "billing_profile_created",
            extra={
                "profile_id": str(profile.id),
                "client_id": str(client_id),
                "is_default": is_default,
            },
        )
        return profile

    # ─── Read ────────────────────────────────────────────────────────────────

    async def list_for_client(self, client_id: uuid.UUID) -> list[BillingProfile]:
        """Return profiles ordered: default first, then by created_at ASC."""
        stmt = (
            select(BillingProfile)
            .where(BillingProfile.client_id == client_id)
            .order_by(BillingProfile.is_default.desc(), BillingProfile.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def get(self, profile_id: uuid.UUID) -> BillingProfile:
        """Fetch a single profile by ID. Raises BillingProfileNotFoundError if missing."""
        return await self._load(profile_id)

    # ─── Mutation ────────────────────────────────────────────────────────────

    async def update(
        self, profile_id: uuid.UUID, payload: BillingProfileUpdate
    ) -> BillingProfile:
        """
        Apply a partial update to a billing profile.

        If tax_id changes, uniqueness is re-checked before flushing.
        """
        profile = await self._load(profile_id)

        update_data = payload.model_dump(exclude_unset=True)
        if "tax_id" in update_data:
            new_tax_id = update_data["tax_id"]
            if new_tax_id != profile.tax_id:
                await self._assert_unique_tax_id(
                    profile.client_id, new_tax_id, exclude_id=profile_id
                )

        for field, value in update_data.items():
            setattr(profile, field, value)

        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_billing_profile_client_tax_id" in str(exc.orig):
                await self.session.rollback()
                raise DuplicateTaxIdError(profile.client_id, profile.tax_id) from exc
            raise
        await self.session.refresh(profile)
        return profile

    async def delete(self, profile_id: uuid.UUID) -> None:
        """
        Delete a billing profile.

        If the profile is the default:
          - If it is the only profile → raise CannotDeleteOnlyDefaultError (409).
          - If siblings exist → auto-promote the oldest (created_at ASC, id ASC) sibling.
        Non-default profiles are deleted immediately.
        Both the promotion and deletion are flushed together for atomicity.
        """
        profile = await self._load(profile_id)

        if profile.is_default:
            stmt = (
                select(BillingProfile)
                .where(
                    BillingProfile.client_id == profile.client_id,
                    BillingProfile.id != profile_id,
                )
                .order_by(BillingProfile.created_at.asc(), BillingProfile.id.asc())
            )
            others = (await self.session.execute(stmt)).scalars().all()
            if not others:
                raise CannotDeleteOnlyDefaultError(profile_id)
            others[0].is_default = True

        await self.session.delete(profile)
        await self.session.flush()
        logger.info("billing_profile_deleted", extra={"profile_id": str(profile_id)})

    async def set_default(self, profile_id: uuid.UUID) -> BillingProfile:
        """
        Promote a profile to default and demote all others in the same client.

        Both writes are flushed together — zero-default is impossible mid-flush.
        """
        profile = await self._load(profile_id)

        await self.session.execute(
            update(BillingProfile)
            .where(
                BillingProfile.client_id == profile.client_id,
                BillingProfile.id != profile_id,
            )
            .values(is_default=False)
        )
        profile.is_default = True
        await self.session.flush()
        await self.session.refresh(profile)
        return profile
