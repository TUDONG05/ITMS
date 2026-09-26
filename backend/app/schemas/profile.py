"""Pydantic schemas for UC-5 – Quản lý hồ sơ cá nhân."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class MentorSummarySchema(BaseSchema):
    id: uuid.UUID
    full_name: str
    email: str


class InternProfileRead(BaseSchema):
    """Response schema cho GET /profile  và  PATCH /profile."""

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    role: str
    status: str
    created_at: datetime
    mentor: MentorSummarySchema | None = None


class UpdateProfileRequest(BaseModel):
    """Chỉ cho phép cập nhật phone và avatar_url; full_name và email không được sửa."""

    phone: str | None = Field(default=None, max_length=20)
    avatar_url: str | None = Field(default=None, max_length=2048)
