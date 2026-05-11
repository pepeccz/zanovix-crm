"""Lead model — core aggregate for the CRM lead capture MVP."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.user import User


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "vertical IN ('clinicas_dentales','general')",
            name="ck_lead_vertical",
        ),
        CheckConstraint(
            "channel IN ('email_marketing','cold_calling','networking',"
            "'referral','web_form','other')",
            name="ck_lead_channel",
        ),
        CheckConstraint(
            "status IN ('new','contacted','qualified','disqualified','converted')",
            name="ck_lead_status",
        ),
        Index("ix_lead_email", "email"),
        Index("ix_lead_status", "status"),
        Index("ix_lead_vertical", "vertical"),
        Index("ix_lead_owner_id", "owner_id"),
        Index("ix_lead_created_at_desc", "created_at"),
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
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vertical: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    converted_client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner: Mapped[User | None] = relationship("User", lazy="selectin")
