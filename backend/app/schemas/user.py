import re
import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.models.enums import UserRole, UserStatus
from app.schemas.base import BaseSchema

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserBase(BaseSchema):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=150)
    role: UserRole = UserRole.INTERN
    status: UserStatus = UserStatus.ACTIVE
    phone: str | None = Field(default=None, max_length=20)
    avatar_url: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if cls.__name__ == "UserRead":
            return value
        normalized_email = value.strip().casefold()
        if not EMAIL_REGEX.match(normalized_email):
            raise ValueError("Email không hợp lệ.")
        return normalized_email


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseSchema):
    full_name: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    role: UserRole | None = None


class UserStatusUpdate(BaseSchema):
    status: UserStatus
