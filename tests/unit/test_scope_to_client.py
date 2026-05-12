"""
Unit tests for api/deps/scope.py — scope_to_client dependency.

Tests three branches per design §D1:
1. client_user with valid client_id → returns (user, client_id)
2. Internal role (admin/comercial/consultor) → raises HTTP 403
3. client_user with client_id IS NULL → raises HTTP 403

No database involved — pure Python with fake User objects.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api.deps.scope import scope_to_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str, client_id: uuid.UUID | None = None) -> object:
    """Build a minimal User-like object for unit testing."""

    class FakeUser:
        pass

    user = FakeUser()
    user.role = role
    user.client_id = client_id
    user.id = uuid.uuid4()
    user.email = f"{role}@test.example"
    user.is_active = True
    return user


# ---------------------------------------------------------------------------
# Branch 1: client_user with a valid client_id → returns (user, client_id)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_user_with_client_id_returns_tuple() -> None:
    """scope_to_client returns (user, client_id) for a properly linked client_user."""
    client_id = uuid.uuid4()
    user = _make_user("client_user", client_id=client_id)

    result_user, result_client_id = await scope_to_client(current_user=user)

    assert result_user is user
    assert result_client_id == client_id


# ---------------------------------------------------------------------------
# Branch 2: internal roles → HTTP 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "comercial", "consultor"])
async def test_internal_role_raises_403(role: str) -> None:
    """Internal roles must not access /api/me/* endpoints — 403 expected."""
    user = _make_user(role, client_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await scope_to_client(current_user=user)

    assert exc_info.value.status_code == 403
    assert "client_user" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Branch 3: client_user with null client_id → HTTP 403 (misconfigured account)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_user_null_client_id_raises_403() -> None:
    """A client_user whose client_id is NULL is misconfigured — must raise 403."""
    user = _make_user("client_user", client_id=None)

    with pytest.raises(HTTPException) as exc_info:
        await scope_to_client(current_user=user)

    assert exc_info.value.status_code == 403
    assert "not linked" in exc_info.value.detail
