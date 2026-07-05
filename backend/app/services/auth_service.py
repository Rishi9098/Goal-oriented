"""
Authentication service: password hashing, JWT creation and verification.
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


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


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.  Raises JWTError on invalid / expired tokens.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def get_user_id_from_token(token: str, expected_type: str = "access") -> str:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}'")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Token missing subject")
    return user_id
