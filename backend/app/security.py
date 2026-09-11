import datetime as dt
import hashlib
import secrets
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from app.config import get_settings

settings = get_settings()


def validate_password_strength(password: str) -> Optional[str]:
    """
    Validate password requirements:
    - Minimum 8 characters
    - Maximum 72 bytes (bcrypt input limit)
    - Not pure whitespace
    Returns error message if invalid, None if valid.
    """
    if not password or len(password.strip()) < 8:
        return "Password must be at least 8 characters long."
    if len(password.encode("utf-8")) > 72:
        return "Password must not exceed 72 bytes."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def generate_verification_code() -> str:
    """Generate a cryptographically random 6-digit numerical code (100000 - 999999)."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def hash_code(code: str) -> str:
    """Hash a verification/reset code with SHA-256 for secure database storage."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def verify_code_hash(code: str, stored_hash: str) -> bool:
    """Constant-time comparison of hashed code."""
    candidate_hash = hash_code(code)
    return secrets.compare_digest(candidate_hash, stored_hash)


def create_access_token(subject: str) -> str:
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None
