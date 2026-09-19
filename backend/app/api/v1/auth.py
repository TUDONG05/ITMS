from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.service import Account, get_auth_service
from app.core.settings import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.casefold().strip()
        if "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        return normalized_email


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: AuthenticatedUser


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


def _serialize_account(account: Account) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(account.id),
        email=account.email,
        full_name=account.full_name,
        role=account.role,
    )
