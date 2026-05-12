"""Message model — client communication thread entry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.client import Client
    from database.models.user import User


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_client_id", "client_id"),
        Index("ix_messages_client_id_created_at", "client_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Reserved for future file attachments; empty list default (no uploads in slice 5)
    attachments_json: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="'[]'::jsonb"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    client: Mapped[Client] = relationship(
        "Client", foreign_keys=[client_id], lazy="select"
    )
    sender: Mapped[User | None] = relationship(
        "User", foreign_keys=[sender_user_id], lazy="select"
    )
