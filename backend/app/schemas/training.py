import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import InternshipPosition
from app.schemas.base import BaseSchema
from app.schemas.document import DocumentSummary

# ---------------------------------------------------------------------------
# Roadmap schemas
# ---------------------------------------------------------------------------


class RoadmapCreate(BaseSchema):
    position: InternshipPosition
    name: str = Field(..., max_length=200)
    description: str | None = None
    status: str = "DRAFT"


class RoadmapUpdate(BaseSchema):
    position: InternshipPosition | None = None
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    status: str | None = None


class RoadmapRead(BaseSchema):
    position: InternshipPosition | None = None
    id: uuid.UUID
    name: str
    description: str | None = None
    status: str
    created_by: uuid.UUID | None = None
    phase_count: int = 0
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Phase schemas
# ---------------------------------------------------------------------------


class PhaseCreate(BaseSchema):
    name: str = Field(..., max_length=200)
    description: str | None = None
    order_no: int
    roadmap_id: uuid.UUID


class PhaseUpdate(BaseSchema):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    order_no: int | None = None


class PhaseRead(BaseSchema):
    id: uuid.UUID
    roadmap_id: uuid.UUID
    name: str
    description: str | None = None
    order_no: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# LearningContent schemas
# ---------------------------------------------------------------------------


class LearningContentCreate(BaseSchema):
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    phase_id: uuid.UUID
    title: str = Field(..., max_length=255)
    description: str | None = None
    type: str  # LESSON | DOCUMENT | VIDEO | LINK
    content: str | None = None
    resource_url: str | None = None
    order_no: int


class LearningContentUpdate(BaseSchema):
    document_ids: list[uuid.UUID] | None = Field(None, max_length=100)
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    type: str | None = None
    content: str | None = None
    resource_url: str | None = None
    order_no: int | None = None


class LearningContentRead(BaseSchema):
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    documents: list[DocumentSummary] = Field(default_factory=list)
    id: uuid.UUID
    phase_id: uuid.UUID
    title: str
    description: str | None = None
    type: str
    content: str | None = None
    resource_url: str | None = None
    order_no: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Quiz schemas
# ---------------------------------------------------------------------------


class QuizCreate(BaseSchema):
    phase_id: uuid.UUID
    title: str = Field(..., max_length=255)
    description: str | None = None
    duration_minutes: int
    pass_score: float
    max_attempts: int


class QuizUpdate(BaseSchema):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    duration_minutes: int | None = None
    pass_score: float | None = None
    max_attempts: int | None = None


class QuizRead(BaseSchema):
    id: uuid.UUID
    phase_id: uuid.UUID
    title: str
    description: str | None = None
    duration_minutes: int
    pass_score: float
    max_attempts: int
    status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Question schemas
# ---------------------------------------------------------------------------


class QuestionCreate(BaseSchema):
    quiz_id: uuid.UUID
    content: str
    type: str = "SINGLE_CHOICE"  # SINGLE_CHOICE | MULTIPLE_CHOICE | TRUE_FALSE | TEXT
    options: Any | None = None
    correct_answer: Any | None = None
    score: float | None = 10.0
    order_no: int | None = None


class QuestionUpdate(BaseSchema):
    content: str | None = None
    type: str | None = None
    options: Any | None = None
    correct_answer: Any | None = None
    score: float | None = None
    order_no: int | None = None


class QuestionRead(BaseSchema):
    id: uuid.UUID
    quiz_id: uuid.UUID
    content: str
    type: str
    options: Any | None = None
    correct_answer: Any | None = None
    score: float | None = None
    order_no: int | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Composite / detail schemas
# ---------------------------------------------------------------------------


class PhaseDetailRead(PhaseRead):
    contents: list[LearningContentRead] = []
    quiz_count: int = 0


class RoadmapDetailRead(RoadmapRead):
    phases: list[PhaseDetailRead] = []
