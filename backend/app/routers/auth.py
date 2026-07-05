import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
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
    RefreshRequest,
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


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
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
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        user_id = get_user_id_from_token(body.refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


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
