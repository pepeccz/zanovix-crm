"""
Message service — business logic for the Message aggregate.

Design principles (design §D2, §D9):
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- client_id is always an explicit parameter — no scoping via hidden context.
- list_messages supports an optional `since` datetime for polling (spec §messages-polling).
- create_message writes a message_sent activity log entry.
- services flush; routes commit.
- attachments_json defaults to [] (no upload support in this slice, design §D10).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.message import MessageCreate
from api.services import activity_log_service
from database.models.message import Message

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


class MessageService:
    """
    Service layer for the Message aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Read ───────────────────────────────────────────────────────────────

    async def list_messages(
        self,
        client_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        since: datetime | None = None,
    ) -> tuple[list[Message], int]:
        """
        Return a paginated list of messages for a client, ordered by created_at ASC
        (oldest first — natural chat thread order).

        Optional `since` filter: only messages with created_at > since are returned.
        This supports the frontend polling contract (spec §messages-polling, design §D9).

        Args:
            client_id: The client whose messages to fetch (always required).
            limit:     Maximum number of messages to return (default 50).
            offset:    Number of messages to skip.
            since:     ISO-8601 datetime — return only messages newer than this timestamp.
        """
        stmt = (
            select(Message)
            .where(Message.client_id == client_id)
            .order_by(Message.created_at.asc())
        )
        count_stmt = select(func.count(Message.id)).where(Message.client_id == client_id)

        if since is not None:
            stmt = stmt.where(Message.created_at > since)
            count_stmt = count_stmt.where(Message.created_at > since)

        stmt = stmt.limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    # ─── Write ──────────────────────────────────────────────────────────────

    async def create_message(
        self,
        body: MessageCreate,
        *,
        client_id: uuid.UUID,
        sender_user_id: uuid.UUID,
    ) -> Message:
        """
        Persist a new Message and write a message_sent activity log entry.

        Attachments are not supported in this slice (design §D10). The column
        is reserved and defaults to [].

        services flush; routes commit.

        Returns:
            The flushed Message ORM instance.
        """
        message = Message(
            client_id=client_id,
            sender_user_id=sender_user_id,
            body=body.body,
            attachments_json=[],
        )
        self.session.add(message)
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client_id,
            kind="message_sent",
            body=f"Message sent (len={len(body.body)})",
            actor_user_id=sender_user_id,
        )

        await self.session.refresh(message)
        logger.info(
            "message_created",
            extra={
                "message_id": str(message.id),
                "client_id": str(client_id),
                "sender_user_id": str(sender_user_id),
            },
        )
        return message
