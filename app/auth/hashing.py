import bcrypt
from app.core.exceptions import ValidationException


def hash_password(password: str) -> str:
    """Converts plain password to bcrypt hash — stored in DB"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks plain password against stored hash — used at login"""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes   = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)