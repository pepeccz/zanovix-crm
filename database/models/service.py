"""Service model — engagement/project delivered to a Client."""

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
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.user import User

if TYPE_CHECKING:
    from database.models.client import Client
    from database.models.milestone import Milestone


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "type IN ('assessment','development','formation')",
            name="ck_service_type",
        ),
        CheckConstraint(
            "state IN ('scoping','running','review','completed','maintenance','paused')",
            name="ck_service_state",
        ),
        Index("ix_service_client_id", "client_id"),
        Index("ix_service_state", "state"),
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
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(
        String(64), nullable=False, default="scoping"
    )
    progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    setup_price_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    monthly_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    score_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Slice 5: assessment diagnostic data (nullable; meaningful only for type='assessment')
    diagnostic_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    owner: Mapped[User | None] = relationship("User", lazy="selectin")
    client: Mapped[Client] = relationship("Client", back_populates="services")
    milestones: Mapped[list[Milestone]] = relationship(
        "Milestone",
        back_populates="service",
        lazy="selectin",
        order_by="Milestone.n",
    )
