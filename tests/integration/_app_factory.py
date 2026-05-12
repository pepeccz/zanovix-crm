"""
Integration test helper — isolated FastAPI app factory.

Problem (W01)
-------------
The singleton ``app`` in ``api.main`` carries a shared ``dependency_overrides``
dict.  When two role-scoped client fixtures both set ``get_current_user`` on
that dict, the second write silently clobbers the first.  Tests that expect a
403 may instead get 200 because they end up running under the wrong role.

Solution
--------
``make_role_app(user)`` builds a *fresh* FastAPI instance via ``build_app()``,
then applies the ``get_current_user`` override on **that** instance only.
Each role-scoped fixture in conftest.py holds its own isolated app, so
overrides never bleed across fixtures — even when two fixtures are active in
the same test.

The production ``app`` singleton is untouched; uvicorn keeps importing it
from ``api.main`` as before.
"""

from __future__ import annotations

from fastapi import FastAPI

from api.auth import get_current_user
from api.main import build_app
from database.models.user import User


def make_role_app(user: User) -> FastAPI:
    """
    Return a fully configured FastAPI app with ``get_current_user`` overridden
    to always return *user*.

    Each call creates an independent app instance — no shared mutable state.
    The override is applied at construction time, so it is stable for the
    entire lifetime of the returned app object.

    Args:
        user: The ORM ``User`` instance that every request will appear to come
              from (role, id, etc. are read directly from this object).

    Returns:
        A ``FastAPI`` instance ready to be wrapped in ``httpx.ASGITransport``.
    """
    role_app = build_app()

    async def _override() -> User:
        return user

    role_app.dependency_overrides[get_current_user] = _override
    return role_app
