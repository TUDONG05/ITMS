from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.auth import _serialize_account, get_current_account
from app.auth.service import Account
from app.schemas.auth import AuthenticatedUser

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=AuthenticatedUser)
def get_me(account: Annotated[Account, Depends(get_current_account)]) -> AuthenticatedUser:
    """Return the authenticated user's server-side identity and role."""
    return _serialize_account(account)
