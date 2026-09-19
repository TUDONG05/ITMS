from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.core.settings import Settings
from app.models.user import User


@dataclass(frozen=True)
class Account:
    id: UUID
    email: str
    full_name: str
    password_hash: str
    role: str
    status: str
    token_version: int


class AuthService:
    """Authenticate persisted users and maintain short-lived active sessions."""

    def __init__(self) -> None:
        self._active_sessions: set[str] = set()

    def login(
        self, db: Session, email: str, password: str, settings: Settings
    ) -> tuple[str, Account]:
        normalized_email = email.casefold().strip()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None or not verify_password(password, user.password_hash):
            raise _invalid_credentials()
        if user.status != "ACTIVE":
            raise _invalid_credentials()

        account = _to_account(user)

        session_id = str(uuid4())
        self._active_sessions.add(session_id)
        return (
            create_access_token(
                subject=str(account.id),
                session_id=session_id,
                token_version=account.token_version,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                expires_in_seconds=settings.access_token_ttl_seconds,
            ),
            account,
        )

    def get_account_from_access_token(self, db: Session, token: str, settings: Settings) -> Account:
        try:
            claims = decode_access_token(
                token,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        except InvalidAccessTokenError:
            raise _invalid_token() from None

        if claims["sid"] not in self._active_sessions:
            raise _invalid_token()
        try:
            user_id = UUID(claims["sub"])
        except ValueError:
            raise _invalid_token() from None

        user = db.get(User, user_id)
        if user is None or user.status != "ACTIVE" or claims["tv"] != user.token_version:
            raise _invalid_token()
        return _to_account(user)


def get_auth_service() -> AuthService:
    """Return the process-local service holding the active session registry."""
    return _auth_service


_auth_service = AuthService()


def _to_account(user: User) -> Account:
    return Account(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        password_hash=user.password_hash,
        role=user.role,
        status=user.status,
        token_version=user.token_version,
    )


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không chính xác.")


def _invalid_token() -> ApiError:
    return ApiError(401, "INVALID_ACCESS_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
