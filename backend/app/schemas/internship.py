import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from app.models.enums import InternshipPeriodStatus, InternshipStatus
from app.schemas.base import BaseSchema


class InternshipPeriodBase(BaseSchema):
    name: str = Field(..., max_length=255)
    start_date: date
    end_date: date
    status: InternshipPeriodStatus = InternshipPeriodStatus.PLANNED

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipPeriodBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipPeriodRead(InternshipPeriodBase):
    id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime


class InternshipBase(BaseSchema):
    intern_id: uuid.UUID
    period_id: uuid.UUID
    status: InternshipStatus = InternshipStatus.PLANNED
    start_date: date
    end_date: date
    note: str | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipRead(InternshipBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
