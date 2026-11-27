import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.models.enums import InternshipPosition
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
    grading_status: str = "AUTO_GRADED"
    ungraded_questions: int = 0
    started_at: datetime
    submitted_at: datetime | None = None


class PendingQuizGradingItemSchema(BaseSchema):
    attempt_id: uuid.UUID
    member_id: uuid.UUID
    intern_id: uuid.UUID
    intern_name: str
    intern_email: str
    quiz_id: uuid.UUID
    quiz_title: str
    attempt_no: int
    submitted_at: datetime
    ungraded_questions: int = 0


class QuizAttemptQuestionGradeView(BaseSchema):
    question_id: uuid.UUID
    content: str
    type: str
    max_score: float
    order_no: int | None = None
    options: list[dict[str, str]] = []
    correct_answer: Any = None
    selected_keys: list[str] = []
    text: str | None = None
    is_correct: bool | None = None
    earned_score: float | None = None
    feedback: str | None = None
    needs_manual_grading: bool = False


class QuizAttemptGradingDetailSchema(BaseSchema):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    pass_score: float
    attempt_no: int
    intern_name: str
    score: float | None = None
    passed: bool | None = None
    grading_status: str = "AUTO_GRADED"
    started_at: datetime
    submitted_at: datetime | None = None
    questions: list[QuizAttemptQuestionGradeView] = []


class QuestionGradeInput(BaseSchema):
    question_id: uuid.UUID
    earned_score: float = Field(..., ge=0)
    feedback: str | None = Field(default=None, max_length=1000)


class QuizAttemptGradeRequest(BaseSchema):
    grades: list[QuestionGradeInput] = Field(..., min_length=1, max_length=200)


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
    position: InternshipPosition | None = None
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
    pending_quiz_gradings: int = 0
    tasks_completed: int = 0
    active_tasks: int = 0


class MentorInternDetailSchema(BaseSchema):
    position: InternshipPosition | None = None
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
    pending_quiz_gradings: int = 0
    recent_interns: list[MentorInternListItem] = []
