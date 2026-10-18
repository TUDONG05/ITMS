from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.settings import Settings
from app.models.auth import AuthSession
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
    avatar_url: str | None = None


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    account: Account
    remember_me: bool

    def __iter__(self) -> Iterator[str | Account]:
        """Giữ tương thích tạm thời với route cũ trong lúc chuyển hợp đồng HTTP."""
        yield self.access_token
        yield self.account


class AuthService:
    """Xác thực người dùng và quản lý phiên đăng nhập bền vững trong DB."""

    def __init__(self) -> None:
        self._password_reset_requests: dict[str, datetime] = {}
        self._password_reset_attempts: dict[str, tuple[int, datetime]] = {}

    def login(
        self,
        db: Session,
        email: str,
        password: str,
        settings: Settings,
        remember_me: bool = False,
    ) -> LoginResult:
        normalized_email = email.casefold().strip()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None or not verify_password(password, user.password_hash):
            raise _invalid_credentials()
        if user.status != "ACTIVE":
            raise ApiError(
                403,
                "ACCOUNT_LOCKED",
                "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.",
            )

        now = datetime.now(UTC)
        session_id = uuid4()
        refresh_token = create_refresh_token(session_id)
        ttl = (
            settings.remembered_refresh_ttl_seconds
            if remember_me
            else settings.session_refresh_ttl_seconds
        )
        auth_session = AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            remember_me=remember_me,
            expires_at=now + timedelta(seconds=ttl),
            last_used_at=now,
            created_at=now,
        )
        db.add(auth_session)
        db.commit()

        account = _to_account(user)
        return LoginResult(
            access_token=_issue_access_token(account, auth_session.id, settings),
            refresh_token=refresh_token,
            account=account,
            remember_me=remember_me,
        )

    def get_account_from_access_token(self, db: Session, token: str, settings: Settings) -> Account:
        claims = self._decode_access_token(token, settings)
        try:
            session_id = UUID(str(claims["sid"]))
            user_id = UUID(str(claims["sub"]))
        except (KeyError, ValueError):
            raise _invalid_token() from None

        auth_session = db.get(AuthSession, session_id)
        if (
            auth_session is None
            or auth_session.user_id != user_id
            or not _session_is_active(auth_session)
        ):
            raise _invalid_token()
        return self._account_for_claims(db, claims)

    def refresh(self, db: Session, token: str, settings: Settings) -> LoginResult:
        auth_session = self._get_refresh_session(db, token)
        user = db.get(User, auth_session.user_id)
        if user is None or user.status != "ACTIVE":
            auth_session.revoked_at = datetime.now(UTC)
            db.commit()
            raise _invalid_refresh_token()

        old_hash = hash_refresh_token(token)
        new_refresh_token = create_refresh_token(auth_session.id)
        new_hash = hash_refresh_token(new_refresh_token)
        now = datetime.now(UTC)
        result = db.execute(
            update(AuthSession)
            .where(
                AuthSession.id == auth_session.id,
                AuthSession.refresh_token_hash == old_hash,
                AuthSession.revoked_at.is_(None),
            )
            .values(refresh_token_hash=new_hash, last_used_at=now)
        )
        if result.rowcount != 1:
            db.rollback()
            raise _invalid_refresh_token()
        db.commit()

        account = _to_account(user)
        return LoginResult(
            access_token=_issue_access_token(account, auth_session.id, settings),
            refresh_token=new_refresh_token,
            account=account,
            remember_me=auth_session.remember_me,
        )

    def logout(self, db: Session, refresh_token: str, settings: Settings) -> None:
        del settings
        auth_session = self._get_refresh_session(db, refresh_token)
        auth_session.revoked_at = datetime.now(UTC)
        db.commit()

    def change_password(
        self, db: Session, account: Account, current_password: str, password: str
    ) -> None:
        user = db.get(User, account.id)
        if user is None or not verify_password(current_password, user.password_hash):
            raise ApiError(400, "INVALID_CURRENT_PASSWORD", "Mật khẩu hiện tại không chính xác.")
        self._set_password(user, password)
        self._revoke_user_sessions(db, user.id)
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
        self._revoke_user_sessions(db, user.id)
        self._password_reset_attempts.pop(normalized_email, None)
        db.commit()

    def _can_send_password_reset(self, email: str) -> bool:
        previous_request = self._password_reset_requests.get(email)
        return previous_request is None or datetime.now(UTC) - previous_request >= timedelta(
            minutes=1
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

    def _decode_access_token(self, token: str, settings: Settings) -> dict[str, object]:
        try:
            return decode_access_token(
                token,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        except InvalidAccessTokenError:
            raise _invalid_token() from None

    def _account_for_claims(self, db: Session, claims: dict[str, object]) -> Account:
        try:
            user_id = UUID(str(claims["sub"]))
        except (KeyError, ValueError):
            raise _invalid_token() from None
        user = db.get(User, user_id)
        if user is None or user.status != "ACTIVE" or claims["tv"] != user.token_version:
            raise _invalid_token()
        return _to_account(user)

    def _get_refresh_session(self, db: Session, token: str) -> AuthSession:
        try:
            session_id_text, secret = token.split(".", 1)
            session_id = UUID(session_id_text)
            if not secret:
                raise ValueError
        except (AttributeError, ValueError):
            raise _invalid_refresh_token() from None

        auth_session = db.get(AuthSession, session_id)
        if (
            auth_session is None
            or not _session_is_active(auth_session)
            or not hmac.compare_digest(
                auth_session.refresh_token_hash,
                hash_refresh_token(token),
            )
        ):
            raise _invalid_refresh_token()
        return auth_session

    def _set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        user.password_changed_at = datetime.now(UTC)
        user.token_version += 1

    def _revoke_user_sessions(self, db: Session, user_id: UUID) -> None:
        db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )


def get_auth_service() -> AuthService:
    """Trả về service không chứa trạng thái phiên theo process."""
    return _auth_service


_auth_service = AuthService()


def _issue_access_token(account: Account, session_id: UUID, settings: Settings) -> str:
    return create_access_token(
        subject=str(account.id),
        session_id=str(session_id),
        token_version=account.token_version,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_in_seconds=settings.access_token_ttl_seconds,
    )


def _to_account(user: User) -> Account:
    return Account(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        password_hash=user.password_hash,
        role=user.role,
        status=user.status,
        token_version=user.token_version,
        avatar_url=user.avatar_url,
    )


def _session_is_active(auth_session: AuthSession) -> bool:
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return auth_session.revoked_at is None and expires_at > datetime.now(UTC)


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không chính xác.")


def _invalid_token() -> ApiError:
    return ApiError(401, "INVALID_ACCESS_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")


def _invalid_refresh_token() -> ApiError:
    return ApiError(401, "INVALID_REFRESH_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")


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
