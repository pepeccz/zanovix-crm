"""ActivityLog model — immutable audit trail for client-scoped events."""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('stage_change','contact_added','contact_updated',"
            "'service_started','service_state_change','milestone_completed',"
            "'lead_converted','note')",
            name="ck_activity_log_kind",
        ),
        # Composite descending index for the default list query (created_at DESC)
        Index(
            "ix_activity_log_client_id_created_at",
            "client_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Immutable log — no updated_at
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
