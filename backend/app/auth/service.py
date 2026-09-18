from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.settings import Settings


@dataclass(frozen=True)
class Account:
    id: UUID
    email: str
    full_name: str
    password_hash: str
    role: str
    status: str


class AuthService:
    """Development-only account store that will be replaced by the M01 repository."""

    def __init__(self) -> None:
        account = Account(
            id=UUID("a0b59b90-3c25-4b08-92d5-e04269c9da31"),
            email="intern@itms.local",
            full_name="Thực tập sinh Demo",
            password_hash=hash_password("Intern@12345"),
            role="INTERN",
            status="ACTIVE",
        )
        self._accounts_by_email = {account.email: account}
        self._accounts_by_id = {str(account.id): account}
        self._active_sessions: set[str] = set()

    def login(self, email: str, password: str, settings: Settings) -> tuple[str, Account]:
        account = self._accounts_by_email.get(email.casefold().strip())
        if account is None or not verify_password(password, account.password_hash):
            raise _invalid_credentials()
        if account.status != "ACTIVE":
            raise _invalid_credentials()

        session_id = str(uuid4())
        self._active_sessions.add(session_id)
        return (
            create_access_token(
                subject=str(account.id),
                session_id=session_id,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                expires_in_seconds=settings.access_token_ttl_seconds,
            ),
            account,
        )

    def get_account_from_access_token(self, token: str, settings: Settings) -> Account:
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
        account = self._accounts_by_id.get(claims["sub"])
        if account is None or account.status != "ACTIVE":
            raise _invalid_token()
        return account


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService()


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không chính xác.")


def _invalid_token() -> ApiError:
    return ApiError(401, "INVALID_ACCESS_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
