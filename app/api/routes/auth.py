from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt import create_token
from app.core.exceptions import AuthException, ValidationException
from app.core.logging import log

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    is_admin: bool


# ── Routes ────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # validate password length
    if len(body.password) < 6:
        raise ValidationException("Password must be at least 6 characters")

    if len(body.password) > 72:
        raise ValidationException("Password cannot exceed 72 characters")

    # check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise ValidationException("Email already registered")

    # create user
    user = User(
        email     = body.email,
        hashed_pw = hash_password(body.password),
        is_admin  = False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # create token
    token = create_token(user_id=user.id, is_admin=user.is_admin)

    log.info("user_registered", user_id=user.id, email=user.email)

    return TokenResponse(
        access_token = token,
        user_id      = user.id,
        email        = user.email,
        is_admin     = user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # find user by email
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    # never say "email not found" — always say "invalid credentials"
    # this prevents attackers from knowing which emails exist
    if not user or not verify_password(body.password, user.hashed_pw):
        raise AuthException("Invalid email or password")

    # create token
    token = create_token(user_id=user.id, is_admin=user.is_admin)

    log.info("user_logged_in", user_id=user.id, email=user.email)

    return TokenResponse(
        access_token = token,
        user_id      = user.id,
        email        = user.email,
        is_admin     = user.is_admin,
    )


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db)):
    """Temporary test route — we will protect this properly later"""
    return {"message": "auth is working"}