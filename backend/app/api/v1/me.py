from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.auth import _serialize_account
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import AuthenticatedUser

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=AuthenticatedUser)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> AuthenticatedUser:
    """Trả về danh tính và vai trò được xác minh phía server."""
    return _serialize_account(user)
