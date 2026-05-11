"""
Contact service — business logic for the Contact aggregate.

Design principles:
- NO FastAPI dependency leak: this module imports nothing from fastapi.
- All methods are async and receive an AsyncSession from the dependency injection layer.
- services flush; routes commit.
- Domain exceptions are raised here and mapped to HTTP responses in api/errors.py.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.contact import ContactCreate, ContactUpdate
from api.services import activity_log_service
from api.services.exceptions import ClientNotFoundError, ContactNotFoundError
from database.models.client import Client
from database.models.contact import Contact
from database.models.user import User

logger = logging.getLogger(__name__)


class ContactService:
    """
    Service layer for the Contact aggregate.

    Instantiated per-request with an AsyncSession. All public methods are async.
    Convention: services flush; routes commit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_client(self, client_id: uuid.UUID) -> Client:
        """Fetch client by id; raise ClientNotFoundError if missing."""
        stmt = select(Client).where(Client.id == client_id)
        client = (await self.session.execute(stmt)).scalar_one_or_none()
        if client is None:
            raise ClientNotFoundError(client_id)
        return client

    async def list_contacts(self, client_id: uuid.UUID) -> list[Contact]:
        """
        Return all contacts for a given client, ordered by name.

        # services flush; routes commit.
        """
        stmt = (
            select(Contact)
            .where(Contact.client_id == client_id)
            .order_by(Contact.name)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def get_contact(
        self,
        client_id: uuid.UUID,
        contact_id: uuid.UUID,
    ) -> Contact:
        """
        Fetch a single contact scoped to the given client.

        # services flush; routes commit.

        Raises:
            ContactNotFoundError: if not found under this client.
        """
        stmt = select(Contact).where(
            Contact.id == contact_id,
            Contact.client_id == client_id,
        )
        contact = (await self.session.execute(stmt)).scalar_one_or_none()
        if contact is None:
            raise ContactNotFoundError(contact_id)
        return contact

    async def create_contact(
        self,
        client_id: uuid.UUID,
        body: ContactCreate,
        actor_user_id: uuid.UUID,
    ) -> Contact:
        """
        Persist a new Contact under the given client and append a 'contact_added' activity log.

        # services flush; routes commit.

        Raises:
            ClientNotFoundError: if the parent client does not exist.
        """
        # Validate client exists
        await self._get_client(client_id)

        contact = Contact(
            client_id=client_id,
            name=body.name,
            role=body.role,
            email=body.email,
            phone=body.phone,
            is_primary=body.is_primary if body.is_primary is not None else False,
        )
        self.session.add(contact)
        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client_id,
            kind="contact_added",
            body=f"Contact '{contact.name}' added",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(contact)
        logger.info(
            "contact_created",
            extra={
                "contact_id": str(contact.id),
                "client_id": str(client_id),
                "actor_user_id": str(actor_user_id),
            },
        )
        return contact

    async def update_contact(
        self,
        client_id: uuid.UUID,
        contact_id: uuid.UUID,
        body: ContactUpdate,
        actor_user_id: uuid.UUID,
    ) -> Contact:
        """
        Patch a contact and append a 'contact_updated' activity log entry.

        # services flush; routes commit.

        Raises:
            ContactNotFoundError: if not found under this client.
        """
        contact = await self.get_contact(client_id, contact_id)

        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact, field, value)

        await self.session.flush()

        await activity_log_service.append_activity(
            self.session,
            client_id=client_id,
            kind="contact_updated",
            body=f"Contact '{contact.name}' updated",
            actor_user_id=actor_user_id,
        )

        await self.session.refresh(contact)
        return contact

    async def delete_contact(
        self,
        client_id: uuid.UUID,
        contact_id: uuid.UUID,
    ) -> None:
        """
        Delete a contact. No activity log (deletion is reflected in absence of the record).

        # services flush; routes commit.

        Raises:
            ContactNotFoundError: if not found under this client.
        """
        contact = await self.get_contact(client_id, contact_id)
        await self.session.delete(contact)
        await self.session.flush()
        logger.info(
            "contact_deleted",
            extra={"contact_id": str(contact_id), "client_id": str(client_id)},
        )
