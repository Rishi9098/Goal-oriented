import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.reset_token import PasswordResetToken  # registers model with Base
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_RESET_TOKEN_TTL_HOURS = 1
_CSRF_HEADER_NAME = "X-CSRF-Token"

# The refresh cookie is httpOnly and scoped to the refresh/logout routes only
# (never sent on every request). The CSRF cookie must be readable by frontend
# JS so it can be echoed back as a header — that's the double-submit check.
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _CookieAttrs(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["lax", "none"]
    domain: str | None
    path: str


def _cookie_kwargs(*, path: str, httponly: bool) -> _CookieAttrs:
    # SameSite=None requires Secure; browsers reject the combination
    # SameSite=None + Secure=False outright. In debug (local HTTP dev) we
    # fall back to Lax + non-Secure so the cookie still works over plain
    # http://localhost.
    return {
        "httponly": httponly,
        "secure": not settings.debug,
        "samesite": "none" if not settings.debug else "lax",
        "domain": settings.cookie_domain,
        "path": path,
    }


def _set_auth_cookies(response: Response, *, refresh_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        **_cookie_kwargs(path=_REFRESH_COOKIE_PATH, httponly=True),
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.refresh_token_expire_days * 86400,
        **_cookie_kwargs(path="/", httponly=False),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.refresh_cookie_name, path=_REFRESH_COOKIE_PATH)
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def _read_refresh_token(request: Request) -> str:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh session found"
        )
    return token


def _verify_csrf(request: Request) -> None:
    header_value = request.headers.get(_CSRF_HEADER_NAME)
    cookie_value = request.cookies.get(settings.csrf_cookie_name)
    if not header_value or not cookie_value or not secrets.compare_digest(
        header_value, cookie_value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Missing or invalid CSRF token"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )
    _set_auth_cookies(response, refresh_token=create_refresh_token(str(user.id)))
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    refresh_token = _read_refresh_token(request)
    _verify_csrf(request)

    try:
        user_id = get_user_id_from_token(refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate the refresh token (and its CSRF pair) on every use to shrink the
    # replay window if a token is ever leaked.
    _set_auth_cookies(response, refresh_token=create_refresh_token(user_id))
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.password is not None:
        current_user.hashed_password = hash_password(body.password)
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    await db.commit()
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> ForgotPasswordResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always return 200 to avoid leaking whether the email exists
    if user is None or not user.is_active:
        return ForgotPasswordResponse(message="If that email exists, a reset link has been sent.")

    plain_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(plain_token),
        expires_at=datetime.now(UTC) + timedelta(hours=_RESET_TOKEN_TTL_HOURS),
    )
    db.add(reset)
    await db.flush()
    await db.commit()

    # No email/SMS provider is wired up yet, so surface the token only in
    # debug builds (used by local dev and the test suite). Returning it
    # unconditionally would let anyone reset any account's password by email
    # address alone.
    return ForgotPasswordResponse(
        message="If that email exists, a reset link has been sent.",
        reset_token=plain_token if settings.debug else None,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> None:
    token_hash = _hash_token(body.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is invalid or has expired.",
        )

    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    record.used_at = datetime.now(UTC)
    db.add(user)
    db.add(record)
    await db.commit()


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password.",
        )
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    await db.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    current_user.is_active = False
    db.add(current_user)
    await db.commit()
