import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import UserRole, UserStatus
from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=150)
    role: UserRole = UserRole.INTERN
    status: UserStatus = UserStatus.ACTIVE
    phone: str | None = Field(default=None, max_length=20)
    avatar_url: str | None = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
