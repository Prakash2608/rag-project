from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.db.session import get_db
from app.db.models import User
from app.auth.jwt import decode_token
from app.core.config import settings
from app.core.exceptions import AuthException, PermissionException
from app.core.logging import log

bearer_scheme = HTTPBearer()


# ── Redis ─────────────────────────────────────────────────────

async def get_redis():
    """Redis connection dependency"""
    client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()


# ── Current user ──────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT token and returns the current logged in user.
    Use this in any protected route.
    """
    token   = credentials.credentials
    payload = decode_token(token)          # raises AuthException if invalid
    user_id = payload.get("sub")

    if not user_id:
        raise AuthException("Token missing user id")

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()

    if not user:
        raise AuthException("User no longer exists")

    log.debug("auth_ok", user_id=user_id)
    return user


# ── Admin user ────────────────────────────────────────────────

async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Only allows admin users.
    Use this in admin routes like /admin/usage
    """
    if not current_user.is_admin:
        raise PermissionException("Admin access required")
    return current_user