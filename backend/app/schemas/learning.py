"""Schema API UC-6: Intern học tập và đào tạo.

Các schema dành cho Intern tuyệt đối không có trường đáp án đúng của câu hỏi.
"""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema

# ---------------------------------------------------------------------------
# Lộ trình, giai đoạn, nội dung
# ---------------------------------------------------------------------------


class LearningProgressRead(BaseSchema):
    content_id: uuid.UUID
    status: str  # NOT_STARTED | IN_PROGRESS | COMPLETED
    progress_percent: float
    completed_at: datetime | None = None


class LearningContentItem(BaseSchema):
    id: uuid.UUID
    title: str
    description: str | None = None
    type: str  # LESSON | DOCUMENT | VIDEO | LINK
    resource_url: str | None = None
    order_no: int
    status: str = "NOT_STARTED"
    progress_percent: float = 0
    completed_at: datetime | None = None


class LearningContentDetail(LearningContentItem):
    phase_id: uuid.UUID
    phase_name: str
    content: str | None = None


class LearningQuizSummary(BaseSchema):
    id: uuid.UUID
    title: str
    description: str | None = None
    duration_minutes: int
    pass_score: float
    max_attempts: int
    status: str  # PUBLISHED | CLOSED
    question_count: int = 0
    attempts_used: int = 0
    best_score: float | None = None
    passed: bool = False


class LearningPhaseItem(BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None = None
    order_no: int
    progress_percent: float = 0
    completed_contents: int = 0
    total_contents: int = 0
    contents: list[LearningContentItem] = []
    quizzes: list[LearningQuizSummary] = []


class LearningRoadmapRead(BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None = None
    progress_percent: float = 0
    completed_contents: int = 0
    total_contents: int = 0
    phases: list[LearningPhaseItem] = []


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


class QuizOption(BaseSchema):
    key: str
    text: str


class QuizQuestionPublic(BaseSchema):
    """Câu hỏi gửi cho Intern: không kèm đáp án đúng."""

    id: uuid.UUID
    content: str
    type: str  # SINGLE_CHOICE | MULTIPLE_CHOICE | TRUE_FALSE | TEXT
    options: list[QuizOption] = []
    score: float
    order_no: int | None = None


class AttemptStartedRead(BaseSchema):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    attempt_no: int
    started_at: datetime
    expires_at: datetime
    duration_minutes: int
    resumed: bool = False
    questions: list[QuizQuestionPublic] = []


class AnswerSubmit(BaseSchema):
    question_id: uuid.UUID
    selected_keys: list[str] = Field(default_factory=list, max_length=26)
    text: str | None = Field(default=None, max_length=2000)


class AttemptSubmit(BaseSchema):
    answers: list[AnswerSubmit] = Field(default_factory=list, max_length=200)


class QuestionResult(BaseSchema):
    question_id: uuid.UUID
    # None: câu hỏi chưa thể chấm tự động nên không được tính vào điểm.
    is_correct: bool | None = None
    earned_score: float = 0


class AttemptResultRead(BaseSchema):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    attempt_no: int
    score: float  # thang 0-100, so sánh với pass_score của Quiz
    passed: bool
    earned_points: float
    total_points: float
    ungraded_questions: int = 0
    started_at: datetime
    submitted_at: datetime
    questions: list[QuestionResult] = []


class AttemptSummary(BaseSchema):
    attempt_id: uuid.UUID
    attempt_no: int
    status: str  # IN_PROGRESS | SUBMITTED
    score: float | None = None
    passed: bool | None = None
    started_at: datetime
    submitted_at: datetime | None = None


class QuizResultsRead(BaseSchema):
    quiz_id: uuid.UUID
    title: str
    pass_score: float
    max_attempts: int
    attempts_used: int
    best_score: float | None = None
    passed: bool = False
    attempts: list[AttemptSummary] = []
