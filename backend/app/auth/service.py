from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
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
        self._active_sessions: dict[str, UUID] = {}
        self._password_reset_requests: dict[str, datetime] = {}
        self._password_reset_attempts: dict[str, tuple[int, datetime]] = {}

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
        self._active_sessions[session_id] = account.id
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
        claims = self._validate_access_token(db, token, settings)
        return self._account_for_claims(db, claims)

    def refresh(self, db: Session, token: str, settings: Settings) -> tuple[str, Account]:
        claims = self._validate_access_token(db, token, settings)
        account = self._account_for_claims(db, claims)
        return (
            create_access_token(
                subject=str(account.id),
                session_id=claims["sid"],
                token_version=account.token_version,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                expires_in_seconds=settings.access_token_ttl_seconds,
            ),
            account,
        )

    def logout(self, db: Session, token: str, settings: Settings) -> None:
        claims = self._validate_access_token(db, token, settings)
        self._active_sessions.pop(claims["sid"], None)

    def change_password(
        self, db: Session, account: Account, current_password: str, password: str
    ) -> None:
        user = db.get(User, account.id)
        if user is None or not verify_password(current_password, user.password_hash):
            raise ApiError(400, "INVALID_CURRENT_PASSWORD", "Mật khẩu hiện tại không chính xác.")
        self._set_password(user, password)
        self._revoke_user_sessions(user.id)
        db.commit()

    def create_password_reset_otp(
        self, db: Session, email: str, settings: Settings
    ) -> tuple[str, str] | None:
        normalized_email = email.casefold().strip()
        if not self._can_send_password_reset(normalized_email):
            return None
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None or user.status != "ACTIVE":
            return None
        otp = f"{secrets.randbelow(1_000_000):06d}"
        user.password_reset_token_hash = _hash_reset_secret(user.email, otp, settings)
        user.password_reset_expires_at = datetime.now(UTC) + timedelta(minutes=30)
        self._password_reset_requests[normalized_email] = datetime.now(UTC)
        self._password_reset_attempts.pop(normalized_email, None)
        db.commit()
        return user.email, otp

    def reset_password(
        self, db: Session, email: str, otp: str, password: str, settings: Settings
    ) -> None:
        normalized_email = email.casefold().strip()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if (
            not self._consume_password_reset_attempt(normalized_email)
            or user is None
            or user.password_reset_token_hash != _hash_reset_secret(normalized_email, otp, settings)
            or not _is_reset_token_valid(user)
        ):
            raise ApiError(
                400,
                "INVALID_RESET_OTP",
                "Mã OTP không hợp lệ hoặc đã hết hạn.",
            )
        self._set_password(user, password)
        self._revoke_user_sessions(user.id)
        self._password_reset_attempts.pop(normalized_email, None)
        db.commit()

    def _can_send_password_reset(self, email: str) -> bool:
        previous_request = self._password_reset_requests.get(email)
        return (
            previous_request is None
            or datetime.now(UTC) - previous_request >= timedelta(minutes=1)
        )

    def _consume_password_reset_attempt(self, email: str) -> bool:
        now = datetime.now(UTC)
        attempts, window_started_at = self._password_reset_attempts.get(email, (0, now))
        if now - window_started_at >= timedelta(minutes=30):
            attempts, window_started_at = 0, now
        if attempts >= 5:
            return False
        self._password_reset_attempts[email] = (attempts + 1, window_started_at)
        return True

    def _validate_access_token(
        self, db: Session, token: str, settings: Settings
    ) -> dict[str, object]:
        try:
            claims = decode_access_token(
                token,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        except InvalidAccessTokenError:
            raise _invalid_token() from None

        if self._active_sessions.get(claims["sid"]) is None:
            raise _invalid_token()
        try:
            user_id = UUID(claims["sub"])
        except ValueError:
            raise _invalid_token() from None

        if self._active_sessions[claims["sid"]] != user_id:
            raise _invalid_token()
        return claims

    def _account_for_claims(self, db: Session, claims: dict[str, object]) -> Account:
        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError:
            raise _invalid_token() from None
        user = db.get(User, user_id)
        if user is None or user.status != "ACTIVE" or claims["tv"] != user.token_version:
            raise _invalid_token()
        return _to_account(user)

    def _set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        user.password_changed_at = datetime.now(UTC)
        user.token_version += 1

    def _revoke_user_sessions(self, user_id: UUID) -> None:
        self._active_sessions = {
            session_id: session_user_id
            for session_id, session_user_id in self._active_sessions.items()
            if session_user_id != user_id
        }


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


def _hash_reset_secret(email: str, otp: str, settings: Settings) -> str:
    message = f"{email.casefold().strip()}:{otp}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def _is_reset_token_valid(user: User) -> bool:
    expires_at = user.password_reset_expires_at
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > datetime.now(UTC)
