from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.service import Account, get_auth_service
from app.core.errors import ApiError
from app.core.mail import send_password_reset_otp
from app.core.settings import get_settings
from app.db.session import get_db
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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Authenticate an active account and issue a short-lived access token."""
    settings = get_settings()
    access_token, account = get_auth_service().login(db, payload.email, payload.password, settings)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_ttl_seconds,
        user=_serialize_account(account),
    )


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Account:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "MISSING_ACCESS_TOKEN", "Cần đăng nhập để truy cập tài nguyên này.")
    return get_auth_service().get_account_from_access_token(
        db, credentials.credentials, get_settings()
    )


def _bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "MISSING_ACCESS_TOKEN", "Cần đăng nhập để truy cập tài nguyên này.")
    return credentials.credentials


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    access_token, account = get_auth_service().refresh(db, _bearer_token(credentials), settings)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_ttl_seconds,
        user=_serialize_account(account),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> MessageResponse:
    get_auth_service().logout(db, _bearer_token(credentials), get_settings())
    return MessageResponse(message="Đã đăng xuất.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    account: Annotated[Account, Depends(get_current_account)],
    db: Session = Depends(get_db),
) -> MessageResponse:
    get_auth_service().change_password(db, account, payload.current_password, payload.new_password)
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


def _serialize_account(account: Account) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(account.id),
        email=account.email,
        full_name=account.full_name,
        role=account.role,
    )
