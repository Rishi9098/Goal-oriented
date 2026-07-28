"""
Authentication service: password hashing, JWT creation and verification.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

# Passlib 1.7.4 compatibility patch for bcrypt >= 4.0.0
if not hasattr(bcrypt, "__about__"):
    class __about__:  # type: ignore[no-redef]
        __version__ = getattr(bcrypt, "__version__", "4.1.3")
    bcrypt.__about__ = __about__  # type: ignore[attr-defined]

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # passlib is untyped; CryptContext.hash() is known to return str at runtime.
    return cast(str, pwd_context.hash(password))


def verify_password(plain: str, hashed: str) -> bool:
    # passlib is untyped; CryptContext.verify() is known to return bool at runtime.
    return cast(bool, pwd_context.verify(plain, hashed))


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    # python-jose is untyped; jwt.encode() is known to return str at runtime.
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def create_access_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.  Raises JWTError on invalid / expired tokens.
    """
    # python-jose is untyped; jwt.decode() is known to return dict[str, Any] at runtime.
    return cast(
        dict[str, Any],
        jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        ),
    )


def get_user_id_from_token(token: str, expected_type: str = "access") -> str:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}'")

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Token missing subject")
    return user_id
