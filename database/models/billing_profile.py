"""BillingProfile model — fiscal/billing identity attached to a Client."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.client import Client


class BillingProfile(Base):
    __tablename__ = "billing_profiles"
    __table_args__ = (
        UniqueConstraint("client_id", "tax_id", name="uq_billing_profile_client_tax_id"),
        CheckConstraint(
            "tax_id_type IN ('NIF','CIF','NIE','VAT')",
            name="ck_billing_profile_tax_id_type",
        ),
        CheckConstraint(
            "tax_regime IN ('general','recargo_equivalencia','simplificado','exento','intracomunitario')",
            name="ck_billing_profile_tax_regime",
        ),
        CheckConstraint(
            "char_length(country) = 2",
            name="ck_billing_profile_country_iso2",
        ),
        Index("ix_billing_profile_client_id", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(32), nullable=False)
    tax_id_type: Mapped[str] = mapped_column(String(8), nullable=False)
    tax_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    province: Mapped[str] = mapped_column(String(120), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="ES")
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    client: Mapped["Client"] = relationship("Client", back_populates="billing_profiles")
