import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.learning import (
    AttemptResultRead,
    AttemptStartedRead,
    AttemptSubmit,
    LearningContentDetail,
    LearningProgressRead,
    LearningRoadmapRead,
    QuizResultsRead,
)
from app.services.learning import LearningService

router = APIRouter(prefix="/learning", tags=["learning"])

# UC-6 chỉ dành cho Intern; dữ liệu luôn lấy theo Intern đang đăng nhập.
_intern_only = require_roles([UserRole.INTERN])


@router.get("/roadmap", response_model=LearningRoadmapRead, summary="Lộ trình học của tôi")
def get_my_roadmap(
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> LearningRoadmapRead:
    """Lộ trình được giao: giai đoạn, nội dung, tiến độ và các bài kiểm tra."""
    return LearningService.get_roadmap(db, current_user)


@router.get(
    "/contents/{content_id}",
    response_model=LearningContentDetail,
    summary="Chi tiết nội dung đào tạo",
)
def get_content(
    content_id: uuid.UUID,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> LearningContentDetail:
    return LearningService.get_content(db, current_user, content_id)


@router.post(
    "/contents/{content_id}/start",
    response_model=LearningProgressRead,
    summary="Ghi nhận bắt đầu học một nội dung",
)
def start_content(
    content_id: uuid.UUID,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> LearningProgressRead:
    return LearningService.start_content(db, current_user, content_id)


@router.post(
    "/contents/{content_id}/complete",
    response_model=LearningProgressRead,
    summary="Ghi nhận hoàn thành một nội dung",
)
def complete_content(
    content_id: uuid.UUID,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> LearningProgressRead:
    return LearningService.complete_content(db, current_user, content_id)


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=AttemptStartedRead,
    summary="Bắt đầu hoặc tiếp tục làm bài kiểm tra",
)
def start_quiz_attempt(
    quiz_id: uuid.UUID,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> AttemptStartedRead:
    """Trả đề thi (không kèm đáp án đúng) và thời điểm hết giờ do server tính."""
    return LearningService.start_attempt(db, current_user, quiz_id)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AttemptResultRead,
    summary="Nộp bài kiểm tra và nhận kết quả chấm",
)
def submit_quiz_attempt(
    attempt_id: uuid.UUID,
    payload: AttemptSubmit,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> AttemptResultRead:
    return LearningService.submit_attempt(db, current_user, attempt_id, payload)


@router.get(
    "/quizzes/{quiz_id}/results",
    response_model=QuizResultsRead,
    summary="Kết quả các lần làm bài của tôi",
)
def get_quiz_results(
    quiz_id: uuid.UUID,
    current_user: User = Depends(_intern_only),
    db: Session = Depends(get_db),
) -> QuizResultsRead:
    return LearningService.get_quiz_results(db, current_user, quiz_id)
