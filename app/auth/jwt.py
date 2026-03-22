from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.config import settings
from app.core.exceptions import AuthException
from app.core.logging import log

ALGORITHM   = "HS256"
EXPIRE_HOURS = 8


def create_token(user_id: str, is_admin: bool = False) -> str:
    """Creates a JWT token for the user after login"""
    payload = {
        "sub"      : user_id,
        "is_admin" : is_admin,
        "exp"      : datetime.utcnow() + timedelta(hours=EXPIRE_HOURS),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    log.info("token_created", user_id=user_id, expires_in_hours=EXPIRE_HOURS)
    return token


def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token — raises AuthException if invalid"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload

    except JWTError as e:
        log.warning("token_invalid", error=str(e))
        raise AuthException("Invalid or expired token")