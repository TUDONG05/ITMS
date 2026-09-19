from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.v1.auth import AuthenticatedUser, _serialize_account
from app.auth.service import Account, get_auth_service
from app.core.errors import ApiError
from app.core.settings import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/me", tags=["auth"])
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


@router.get("", response_model=AuthenticatedUser)
def get_me(account: Annotated[Account, Depends(get_current_account)]) -> AuthenticatedUser:
    """Return the authenticated user's server-side identity and role."""
    return _serialize_account(account)
