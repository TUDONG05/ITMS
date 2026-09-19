import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from app.models.enums import InternshipMemberStatus, InternshipStatus
from app.schemas.base import BaseSchema


class InternshipBase(BaseSchema):
    name: str = Field(max_length=200)
    description: str | None = None
    start_date: date
    end_date: date
    status: InternshipStatus = InternshipStatus.DRAFT

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipRead(InternshipBase):
    id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class InternshipMemberBase(BaseSchema):
    internship_id: uuid.UUID
    intern_id: uuid.UUID
    mentor_id: uuid.UUID | None = None
    roadmap_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: InternshipMemberStatus = InternshipMemberStatus.ACTIVE

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipMemberBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self
