import uuid
from datetime import date, datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class InternProfileSchema(BaseSchema):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    status: str


class InternshipBriefSchema(BaseSchema):
    id: uuid.UUID
    name: str
    status: str
    start_date: date | None = None
    end_date: date | None = None


class MentorBriefSchema(BaseSchema):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None


class LearningContentProgressSchema(BaseSchema):
    id: uuid.UUID
    title: str
    type: str
    order_no: int
    progress_percent: float = 0.0
    status: str = "NOT_STARTED"
    completed_at: datetime | None = None


class RoadmapPhaseDetailSchema(BaseSchema):
    id: uuid.UUID
    name: str
    order_no: int
    description: str | None = None
    contents: list[LearningContentProgressSchema] = []


class InternRoadmapDetailSchema(BaseSchema):
    roadmap_id: uuid.UUID | None = None
    roadmap_name: str | None = None
    description: str | None = None
    phases: list[RoadmapPhaseDetailSchema] = []


class QuizAttemptDetailSchema(BaseSchema):
    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    attempt_no: int
    score: float | None = None
    passed: bool | None = None
    started_at: datetime
    submitted_at: datetime | None = None


class MentorAssignmentHistoryItem(BaseSchema):
    action: str = Field(..., description="'ASSIGN' or 'CHANGE'")
    member_id: uuid.UUID
    intern_id: uuid.UUID
    intern_name: str
    old_mentor_id: uuid.UUID | None = None
    old_mentor_name: str | None = None
    new_mentor_id: uuid.UUID
    new_mentor_name: str
    changed_by_id: uuid.UUID
    changed_by_name: str
    changed_at: datetime
    note: str | None = None


class MentorInternListItem(BaseSchema):
    id: uuid.UUID
    intern_id: uuid.UUID
    intern_name: str
    intern_email: str
    intern_phone: str | None = None
    intern_avatar_url: str | None = None
    internship_id: uuid.UUID
    internship_name: str
    roadmap_id: uuid.UUID | None = None
    roadmap_name: str | None = None
    mentor_id: uuid.UUID | None = None
    mentor_name: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    progress_percent: float = 0.0
    quizzes_passed: int = 0
    tasks_completed: int = 0
    active_tasks: int = 0


class MentorInternDetailSchema(BaseSchema):
    id: uuid.UUID
    intern: InternProfileSchema
    internship: InternshipBriefSchema
    mentor: MentorBriefSchema | None = None
    roadmap: InternRoadmapDetailSchema | None = None
    learning_progress: list[LearningContentProgressSchema] = []
    quiz_attempts: list[QuizAttemptDetailSchema] = []
    assignment_history: list[MentorAssignmentHistoryItem] = []
    start_date: date | None = None
    end_date: date | None = None
    status: str


class MentorAssignRequestPayload(BaseSchema):
    member_id: uuid.UUID
    mentor_id: uuid.UUID
    note: str | None = None


class MentorOverviewMetricsSchema(BaseSchema):
    total_interns: int = 0
    active_interns: int = 0
    completed_interns: int = 0
    avg_progress: float = 0.0
    total_quizzes_passed: int = 0
    recent_interns: list[MentorInternListItem] = []
