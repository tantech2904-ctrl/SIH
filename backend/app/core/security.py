from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Returns a $2b$ string.

    Uses 12 rounds to match the previous passlib configuration
    (bcrypt__rounds=12). That means existing hashes in the DB are
    still verifiable and new hashes have the same cost factor.
    """
    if not isinstance(password, str):
        raise TypeError("password must be a str")
    # bcrypt has a 72-byte input limit. Truncate explicitly so
    # behaviour is deterministic and matches the verify path.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns False (never raises) on any malformed input, so a bad
    row in the DB can't crash the login endpoint.

    Note: bcrypt.checkpw transparently reads $2a$, $2b$, and $2y$
    prefixes, so hashes produced by passlib 1.7.4 + bcrypt 4.0.1
    still verify without any re-hash or migration.
    """
    if not isinstance(plain, str) or not isinstance(hashed, str):
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    roles: list[str],
    expires_minutes: int | None = None,
    tenant_id: str = "default",
) -> str:
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        "tenant_id": tenant_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    """Create a refresh token. Returns (token, jti, expires_at).

    The caller is responsible for persisting the jti row so that refresh
    can detect rotation and reuse.
    """
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    """Decode with signature + exp verification. Raises ValueError on failure."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def decode_token_unverified(token: str) -> dict:
    """Decode without signature verification. ONLY used to extract the jti
    from a refresh token during logout, where the caller is already
    authenticated and the DB row lookup is the authoritative check.
    """
    try:
        return jwt.get_unverified_claims(token)
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e