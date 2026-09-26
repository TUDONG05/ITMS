import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole
from app.schemas.base import BaseSchema


class InternshipBase(BaseSchema):
    name: str = Field(..., max_length=200)
    description: str | None = None
    start_date: date
    end_date: date
    status: InternshipStatus = InternshipStatus.DRAFT

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipCreate(InternshipBase):
    pass


class InternshipUpdate(BaseSchema):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: InternshipStatus | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipUpdate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipRead(InternshipBase):
    id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    members_count: int = 0


class InternshipDetailRead(InternshipRead):
    pass


class UserSummary(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    phone: str | None = None
    avatar_url: str | None = None


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
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipMemberCreate(BaseSchema):
    intern_id: uuid.UUID
    mentor_id: uuid.UUID | None = None
    roadmap_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: InternshipMemberStatus = InternshipMemberStatus.ACTIVE

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipMemberCreate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be before start_date")
        return self


class InternshipMemberRead(InternshipMemberBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InternshipMemberDetailRead(InternshipMemberRead):
    intern: UserSummary
    mentor: UserSummary | None = None


class MentorAssignRequest(BaseSchema):
    mentor_id: uuid.UUID | None = None


class InternshipMemberUpdate(BaseSchema):
    mentor_id: uuid.UUID | None = None
    roadmap_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: InternshipMemberStatus | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "InternshipMemberUpdate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be before start_date")
        return self
