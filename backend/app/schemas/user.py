import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import UserRole, UserStatus
from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
