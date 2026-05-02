"""
Idempotent seed script — creates 3 system users (admin / consultor / comercial).

Usage:
    python -m scripts.seed_users
    python scripts/seed_users.py

Passwords are read from environment variables. If unset, dev-only fallbacks
are used and a WARNING is logged to signal that they must be changed.

Env vars:
    SEED_ADMIN_PASSWORD      (default: dev-changeme-admin)
    SEED_CONSULTOR_PASSWORD  (default: dev-changeme-consultor)
    SEED_COMERCIAL_PASSWORD  (default: dev-changeme-comercial)
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from passlib.hash import bcrypt
from sqlalchemy import select

from database.connection import get_async_session
from database.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEV_SUFFIX = "dev-changeme"

USERS_TO_SEED: list[dict[str, str]] = [
    {
        "email": "admin@zanovix.com",
        "display_name": "Admin Zanovix",
        "role": "admin",
        "env_var": "SEED_ADMIN_PASSWORD",
        "default_password": f"{_DEV_SUFFIX}-admin",
    },
    {
        "email": "consultor@zanovix.com",
        "display_name": "Consultor Demo",
        "role": "consultor",
        "env_var": "SEED_CONSULTOR_PASSWORD",
        "default_password": f"{_DEV_SUFFIX}-consultor",
    },
    {
        "email": "comercial@zanovix.com",
        "display_name": "Comercial Demo",
        "role": "comercial",
        "env_var": "SEED_COMERCIAL_PASSWORD",
        "default_password": f"{_DEV_SUFFIX}-comercial",
    },
]


def _resolve_password(env_var: str, default: str, role: str) -> str:
    """Read password from env. Falls back to dev default with a WARN."""
    value = os.environ.get(env_var)
    if value:
        return value
    logger.warning(
        "[seed] %s not set — using insecure dev default for role=%s. "
        "Set %s before running in staging/production.",
        env_var,
        role,
        env_var,
    )
    return default


async def main() -> None:
    created = 0
    skipped = 0

    async with get_async_session() as session:
        for spec in USERS_TO_SEED:
            result = await session.execute(
                select(User).where(User.email == spec["email"])
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                logger.info("[seed] skip  %s (already exists)", spec["email"])
                skipped += 1
                continue

            raw_password = _resolve_password(
                spec["env_var"], spec["default_password"], spec["role"]
            )
            password_hash = bcrypt.hash(raw_password)

            user = User(
                id=uuid.uuid4(),
                email=spec["email"],
                display_name=spec["display_name"],
                role=spec["role"],
                password_hash=password_hash,
                is_active=True,
            )
            session.add(user)
            logger.info("[seed] create %s (role=%s)", spec["email"], spec["role"])
            created += 1

        await session.commit()

    print(f"[seed] created {created} users, skipped {skipped} (already exist)")


if __name__ == "__main__":
    asyncio.run(main())
