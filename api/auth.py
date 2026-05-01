"""
JWT authentication helpers, user resolution, and RBAC.

Extracted from msi-a admin.py and adapted for zanovix-crm User model.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select

from database.connection import get_async_session
from database.models.user import User
from shared.config import get_settings
from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

# Security scheme (Bearer token, optional — cookie fallback)
security = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    role: str,
) -> tuple[str, datetime]:
    """
    Create a signed JWT access token.

    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": email,
        "user_id": str(user_id),
        "role": role,
        "type": "admin",
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def verify_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token (no DB lookup — use for SSE/query-param auth).

    Raises:
        HTTPException 401: Invalid or expired token
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError as exc:
        logger.warning("jwt_validation_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """
    Validate JWT and return the User from the database.

    Token resolution order:
    1. Authorization: Bearer {token} header
    2. admin_token httpOnly cookie fallback

    Raises:
        HTTPException 401: missing/invalid/revoked token or inactive user
    """
    if credentials:
        token = credentials.credentials
    else:
        cookie_token = request.cookies.get("admin_token")
        if not cookie_token:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = cookie_token

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        logger.warning("jwt_validation_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "admin":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Redis blacklist check
    jti = payload.get("jti")
    if jti:
        redis_client = get_redis_client()
        is_blacklisted = await redis_client.get(f"token_blacklist:{jti}")
        if is_blacklisted:
            raise HTTPException(status_code=401, detail="Token has been revoked")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    async with get_async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is disabled")

        return user


def require_role(*roles: str) -> Callable:
    """
    Dependency factory — enforce role-based access control.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint(): ...
    """

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}",
            )
        return current_user

    return check_role
