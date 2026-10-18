"""Schema API UC-12: Quản lý đánh giá (tiêu chí, thang điểm, trọng số, đánh giá)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.base import BaseSchema

CriterionName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
EvaluationType = Literal["PERIODIC", "FINAL"]
CriterionStatus = Literal["ACTIVE", "INACTIVE"]

# ---------------------------------------------------------------------------
# Tiêu chí đánh giá (Admin)
# ---------------------------------------------------------------------------


class CriterionCreate(BaseSchema):
    name: CriterionName
    description: str | None = Field(default=None, max_length=2000)
    max_score: float = Field(gt=0, le=100, description="Thang điểm tối đa của tiêu chí")
    weight: float = Field(ge=0, le=100, description="Trọng số (%)")
    status: CriterionStatus = "ACTIVE"


class CriterionUpdate(BaseSchema):
    name: CriterionName | None = None
    description: str | None = Field(default=None, max_length=2000)
    max_score: float | None = Field(default=None, gt=0, le=100)
    weight: float | None = Field(default=None, ge=0, le=100)
    status: CriterionStatus | None = None


class CriterionRead(BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None = None
    max_score: float
    weight: float
    status: str
    created_at: datetime
    updated_at: datetime


class CriterionListRead(BaseSchema):
    items: list[CriterionRead] = []
    # Tổng trọng số của các tiêu chí đang áp dụng; nên bằng 100 để dễ đọc.
    total_active_weight: float = 0


# ---------------------------------------------------------------------------
# Đánh giá (Mentor lập, Intern xem bản đã công bố)
# ---------------------------------------------------------------------------


class ScoreInput(BaseSchema):
    criterion_id: uuid.UUID
    score: float = Field(ge=0, le=100)


class EvaluationCreate(BaseSchema):
    internship_member_id: uuid.UUID
    evaluation_type: EvaluationType = "PERIODIC"
    scores: list[ScoreInput] = Field(default_factory=list, max_length=50)
    comment: str | None = Field(default=None, max_length=5000)


class EvaluationUpdate(BaseSchema):
    evaluation_type: EvaluationType | None = None
    # None: giữ nguyên điểm đã lưu. Có giá trị: thay toàn bộ bảng điểm của bản nháp.
    scores: list[ScoreInput] | None = Field(default=None, max_length=50)
    comment: str | None = Field(default=None, max_length=5000)


class ScoreRead(BaseSchema):
    criterion_id: uuid.UUID
    name: str
    max_score: float
    weight: float
    score: float


class EvaluationRead(BaseSchema):
    id: uuid.UUID
    internship_member_id: uuid.UUID
    intern_id: uuid.UUID
    intern_name: str
    internship_name: str | None = None
    mentor_id: uuid.UUID
    mentor_name: str | None = None
    evaluation_type: str  # PERIODIC | FINAL
    scores: list[ScoreRead] = []
    total_score: float | None = None  # thang 10, bình quân theo trọng số
    comment: str | None = None
    status: str  # DRAFT | PUBLISHED
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
