from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth.service import Account, LoginResult, get_auth_service
from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.mail import send_password_reset_otp
from app.core.settings import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthenticatedUser,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Xác thực tài khoản, tạo session DB và đặt refresh cookie."""
    settings = get_settings()
    result = get_auth_service().login(
        db,
        payload.email,
        payload.password,
        settings,
        remember_me=payload.remember_me,
    )
    _set_refresh_cookie(response, result, settings)
    return _login_response(result, settings)


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise ApiError(401, "MISSING_REFRESH_TOKEN", "Thiếu cookie làm mới phiên đăng nhập.")
    result = get_auth_service().refresh(db, refresh_token, settings)
    _set_refresh_cookie(response, result, settings)
    return _login_response(result, settings)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MessageResponse:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token:
        try:
            get_auth_service().logout(db, refresh_token, settings)
        except ApiError:
            db.rollback()
    response.delete_cookie(
        settings.refresh_cookie_name,
        path="/api/v1/auth",
        secure=settings.environment == "production",
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return MessageResponse(message="Đã đăng xuất.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> MessageResponse:
    get_auth_service().change_password(db, user, payload.current_password, payload.new_password)
    return MessageResponse(message="Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    settings = get_settings()
    result = get_auth_service().create_password_reset_otp(db, payload.email, settings)
    if result is not None:
        recipient, otp = result
        send_password_reset_otp(settings, recipient, otp)
    return MessageResponse(message="Nếu email tồn tại, mã OTP đặt lại mật khẩu đã được gửi.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    get_auth_service().reset_password(
        db, payload.email, payload.otp, payload.new_password, get_settings()
    )
    return MessageResponse(message="Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.")


def _set_refresh_cookie(response: Response, result: LoginResult, settings: Settings) -> None:
    max_age = settings.remembered_refresh_ttl_seconds if result.remember_me else None
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=result.refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/api/v1/auth",
    )
    response.headers["Cache-Control"] = "no-store"


def _login_response(result: LoginResult, settings: Settings) -> LoginResponse:
    return LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
        expires_in=settings.access_token_ttl_seconds,
        user=_serialize_account(result.account),
    )


def _normalize_avatar_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("/uploads/"):
        return f"/api/v1{url}"
    return url


def _serialize_account(account: Account | User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(account.id),
        email=account.email,
        full_name=account.full_name,
        role=account.role,
        avatar_url=_normalize_avatar_url(account.avatar_url),
    )
