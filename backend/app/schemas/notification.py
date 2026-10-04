from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema

TARGET_TYPES = ("ALL", "ROLE", "USER")
VALID_ROLES = ("INTERN", "MENTOR", "ADMIN")


class NotificationCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    target_type: str = Field(default="ALL")
    target_data: list[Any] | None = Field(None, description="Danh sách role hoặc user_id tuỳ target_type")

    @field_validator("target_type")
    @classmethod
    def _check_target_type(cls, v: str) -> str:
        if v not in TARGET_TYPES:
            raise ValueError(f"target_type must be one of {TARGET_TYPES}")
        return v


class NotificationRead(BaseSchema):
    id: uuid.UUID
    title: str
    content: str
    target_type: str
    target_data: list[Any] | None = None
    created_by: uuid.UUID
    created_at: datetime
    creator_name: str | None = None
    is_read: bool = False
    read_at: datetime | None = None


class NotificationListItem(BaseSchema):
    id: uuid.UUID
    title: str
    content: str
    target_type: str
    created_by: uuid.UUID
    created_at: datetime
    creator_name: str | None = None
    is_read: bool = False
    read_count: int = 0
