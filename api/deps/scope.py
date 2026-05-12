"""
Client-scope authorization dependency.

Provides scope_to_client — a FastAPI dependency that enforces the /api/me/*
endpoint RBAC contract: only client_user role is permitted, and the resolved
client_id is returned to route handlers for query filtering.

Design (design §D1):
  - scope_to_client returns client_id for client_user (used as DB filter).
  - Raises HTTP 403 for any role other than client_user.
  - Raises HTTP 403 for client_user whose client_id IS NULL (misconfigured account).
  - Internal roles (admin/comercial/consultor) MUST NOT use /api/me/* endpoints;
    they have /api/clients/{id}/* routes instead.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException

from api.auth import get_current_user
from database.models.user import User


async def scope_to_client(
    current_user: User = Depends(get_current_user),
) -> tuple[User, uuid.UUID]:
    """
    Resolve the client_id filter for /api/me/* endpoints.

    Only client_user role is permitted. All other roles receive HTTP 403.
    A client_user with client_id IS NULL (misconfigured account) also receives 403.

    Returns:
        Tuple of (current_user, client_id) where client_id is the UUID to filter
        all service-layer queries.

    Raises:
        HTTPException 403: if role != client_user, or if client_user has no client_id.
    """
    if current_user.role != "client_user":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only accessible to client_user accounts.",
        )

    if current_user.client_id is None:
        raise HTTPException(
            status_code=403,
            detail="Account not linked to a client. Contact your account manager.",
        )

    return current_user, current_user.client_id
