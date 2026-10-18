import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from app.models.enums import InternshipMemberStatus, InternshipStatus, RequestType, UserRole
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


class InternshipRequestReview(BaseSchema):
    status: str  # "APPROVED" hoặc "REJECTED"
    review_note: str | None = None


class InternshipProposalCreate(BaseSchema):
    member_id: uuid.UUID
    type: str  # EXTEND | STOP | COMPLETE | TERMINATE
    reason: str = Field(..., min_length=1, max_length=1000)
    requested_end_date: date | None = None

    @model_validator(mode="after")
    def validate_proposal(self) -> "InternshipProposalCreate":
        raw_type = str(self.type).strip().upper()
        if raw_type == "TERMINATE":
            self.type = RequestType.STOP
        elif raw_type in ("EXTEND", "STOP", "COMPLETE"):
            self.type = RequestType(raw_type)
        else:
            raise ValueError(
                f"Invalid proposal type '{raw_type}'. Must be EXTEND, STOP, or COMPLETE."
            )

        if self.type == RequestType.EXTEND and not self.requested_end_date:
            raise ValueError("Ngày kết thúc đề xuất là bắt buộc khi yêu cầu gia hạn (EXTEND).")
        return self


class InternshipStatusHistoryItem(BaseSchema):
    id: uuid.UUID
    action: str  # INITIAL | EXTEND | STOP | COMPLETE
    from_status: str | None = None
    to_status: str
    requested_by_name: str | None = None
    reviewed_by_name: str | None = None
    changed_at: datetime
    reason: str | None = None
    review_note: str | None = None
    proposal_status: str | None = None  # PENDING | APPROVED | REJECTED
    requested_end_date: date | None = None


class InternshipRequestRead(BaseSchema):
    id: uuid.UUID
    internship_member_id: uuid.UUID
    requested_by: uuid.UUID
    type: str  # EXTEND | STOP | COMPLETE
    reason: str
    requested_end_date: date | None = None
    status: str  # PENDING | APPROVED | REJECTED
    reviewed_by: uuid.UUID | None = None
    review_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    intern_id: uuid.UUID | None = None
    intern_name: str | None = None
    intern_email: str | None = None
    mentor_name: str | None = None
    internship_id: uuid.UUID | None = None
    internship_name: str | None = None
