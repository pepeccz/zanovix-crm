"""
Auth routes — login, logout, current user.

Replaces the MSI-a admin.py with a minimal generic auth implementation.
All MSI business endpoints (conversations, cases, tariffs, etc.) have been removed.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from passlib.hash import bcrypt
from pydantic import BaseModel
from sqlalchemy import select

from api.auth import create_access_token, get_current_user, verify_token
from database.connection import get_async_session
from database.models.user import User
from shared.config import get_settings
from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    role: str


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    role: str
    display_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response) -> LoginResponse:
    """Authenticate with email + password. Returns a JWT token."""
    async with get_async_session() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

    if not user or not bcrypt.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    token, expires_at = create_access_token(user.id, user.email, user.role)

    # Set httpOnly cookie (admin panel reads this)
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # TODO: set True in production
    )

    logger.info("user_login", extra={"user_id": str(user.id), "role": user.role})

    return LoginResponse(access_token=token, expires_at=expires_at, role=user.role)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Revoke the current JWT by blacklisting its JTI in Redis."""
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    token: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    else:
        token = request.cookies.get("admin_token")

    if token:
        try:
            payload = verify_token(token)
            jti = payload.get("jti")
            if jti:
                redis_client = get_redis_client()
                settings = get_settings()
                await redis_client.setex(
                    f"token_blacklist:{jti}",
                    settings.JWT_EXPIRE_MINUTES * 60,
                    "1",
                )
        except HTTPException:
            pass  # already invalid — safe to continue

    response.delete_cookie("admin_token")
    logger.info("user_logout", extra={"user_id": str(current_user.id)})
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Return the currently authenticated user."""
    return CurrentUserResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
    )
