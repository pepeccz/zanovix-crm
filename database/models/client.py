"""Client model — core CRM aggregate representing a converted/active client."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.user import User

if TYPE_CHECKING:
    from database.models.billing_profile import BillingProfile
    from database.models.contact import Contact
    from database.models.service import Service


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('lead','discovery_scheduled','discovery_done',"
            "'proposal_sent','active','lost')",
            name="ck_client_stage",
        ),
        Index("ix_client_stage", "stage"),
        Index("ix_client_owner_id", "owner_id"),
        Index("ix_client_name", "name"),
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
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default="lead"
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    mrr_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lifetime_value_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # Relationships
    owner: Mapped[User | None] = relationship(
        "User", foreign_keys="Client.owner_id", lazy="selectin"
    )
    contacts: Mapped[list[Contact]] = relationship(
        "Contact", back_populates="client", lazy="selectin"
    )
    services: Mapped[list[Service]] = relationship(
        "Service", back_populates="client", lazy="selectin"
    )
    billing_profiles: Mapped[list[BillingProfile]] = relationship(
        "BillingProfile",
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
