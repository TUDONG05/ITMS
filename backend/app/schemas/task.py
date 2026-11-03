from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema

TASK_STATUSES = ("TODO", "SUBMITTED", "REVISION_REQUIRED", "COMPLETED", "CANCELLED")
TASK_PRIORITIES = ("LOW", "MEDIUM", "HIGH")
SUBMISSION_STATUSES = ("SUBMITTED", "REVISION_REQUIRED", "ACCEPTED")


class TaskCreate(BaseSchema):
    internship_member_ids: list[uuid.UUID] = Field(..., min_length=1)
    assignment_mode: Literal["GROUP", "INDIVIDUAL"] = "GROUP"
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None)
    deadline: datetime | None = Field(None)
    priority: str = Field(default="MEDIUM")
    attachment_url: str | None = Field(None, description="URL tệp đã upload qua POST /tasks/upload")

    @model_validator(mode="before")
    @classmethod
    def _legacy_recipient(cls, values):
        if isinstance(values, dict) and "internship_member_ids" not in values:
            values = dict(values)
            if values.get("internship_member_id") is not None:
                values["internship_member_ids"] = [values["internship_member_id"]]
        return values

    @field_validator("internship_member_ids")
    @classmethod
    def _dedupe_members(cls, values: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(values))

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, v: str) -> str:
        if v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {TASK_PRIORITIES}")
        return v


class TaskUpdate(BaseSchema):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    deadline: datetime | None = Field(None)
    priority: str | None = Field(None)
    status: str | None = Field(None)
    attachment_url: str | None = Field(None, description="URL mới; null để gỡ đính kèm")

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {TASK_PRIORITIES}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_STATUSES:
            raise ValueError(f"status must be one of {TASK_STATUSES}")
        return v


class TaskAssigneeRead(BaseSchema):
    internship_member_id: uuid.UUID
    intern_id: uuid.UUID
    intern_name: str
    internship_id: uuid.UUID
    internship_name: str
    status: str


class TaskRead(BaseSchema):
    id: uuid.UUID
    internship_member_id: uuid.UUID | None = None
    internship_member_ids: list[uuid.UUID] = Field(default_factory=list)
    assignees: list[TaskAssigneeRead] = Field(default_factory=list)
    assignment_mode: Literal["GROUP", "INDIVIDUAL"] = "GROUP"
    created_by: uuid.UUID
    title: str
    description: str | None = None
    deadline: datetime | None = None
    priority: str | None = None
    status: str
    attachment_url: str | None = None
    created_at: datetime
    updated_at: datetime
    # derived
    intern_name: str | None = None
    internship_name: str | None = None
    submissions_count: int = 0
    comments_count: int = 0
    is_overdue: bool = False
    is_late_submission: bool = False


class SubmissionCreate(BaseSchema):
    content: str | None = Field(None)
    link: str | None = Field(None)
    file_url: str | None = Field(None, alias="attachment_url")

    model_config = {"from_attributes": True, "populate_by_name": True}


class SubmissionRead(BaseSchema):
    id: uuid.UUID
    task_id: uuid.UUID
    internship_member_id: uuid.UUID | None = None
    intern_name: str | None = None
    content: str | None = None
    file_url: str | None = None
    status: str
    review_comment: str | None = None
    reviewed_by: uuid.UUID | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    is_late: bool = False


class TaskReviewPayload(BaseSchema):
    internship_member_id: uuid.UUID | None = None
    decision: str = Field(..., description="'COMPLETED' hoặc 'REVISION_REQUIRED'")
    review_comment: str | None = Field(None)

    @field_validator("decision")
    @classmethod
    def _check_decision(cls, v: str) -> str:
        if v not in ("COMPLETED", "REVISION_REQUIRED"):
            raise ValueError("decision must be 'COMPLETED' or 'REVISION_REQUIRED'")
        return v


class TaskCommentCreate(BaseSchema):
    content: str = Field(..., min_length=1)


class TaskCommentRead(BaseSchema):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    author_name: str | None = None
    author_role: str | None = None
    content: str
    created_at: datetime


class TaskDetailRead(TaskRead):
    submissions: list[SubmissionRead] = []
    comments: list[TaskCommentRead] = []
