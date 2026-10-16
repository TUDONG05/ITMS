import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.evaluation import (
    CriterionCreate,
    CriterionListRead,
    CriterionRead,
    CriterionUpdate,
    EvaluationCreate,
    EvaluationRead,
    EvaluationUpdate,
)
from app.services.evaluation import EvaluationService

# UC-12: tiêu chí do Admin quản lý, Mentor chỉ đọc các tiêu chí đang áp dụng để chấm điểm.
criteria_router = APIRouter(prefix="/evaluation-criteria", tags=["evaluations"])
router = APIRouter(prefix="/evaluations", tags=["evaluations"])

_admin_only = require_roles([UserRole.ADMIN])
_mentor_only = require_roles([UserRole.MENTOR])
_admin_or_mentor = require_roles([UserRole.ADMIN, UserRole.MENTOR])
_all_roles = require_roles([UserRole.ADMIN, UserRole.MENTOR, UserRole.INTERN])


# ── Tiêu chí đánh giá ───────────────────────────────────────────────────────


@criteria_router.get("", response_model=CriterionListRead, summary="Danh sách tiêu chí đánh giá")
def list_criteria(
    status: str | None = Query(None, description="ACTIVE hoặc INACTIVE (chỉ Admin)"),
    current_user: User = Depends(_admin_or_mentor),
    db: Session = Depends(get_db),
) -> CriterionListRead:
    return EvaluationService.list_criteria(db, current_user, status)


@criteria_router.post(
    "",
    response_model=CriterionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tiêu chí đánh giá (Admin)",
)
def create_criterion(
    payload: CriterionCreate,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
) -> CriterionRead:
    return EvaluationService.create_criterion(db, payload)


@criteria_router.put(
    "/{criterion_id}", response_model=CriterionRead, summary="Cập nhật tiêu chí (Admin)"
)
def update_criterion(
    criterion_id: uuid.UUID,
    payload: CriterionUpdate,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
) -> CriterionRead:
    return EvaluationService.update_criterion(db, criterion_id, payload)


@criteria_router.delete(
    "/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa tiêu chí chưa dùng trong đánh giá nào (Admin)",
)
def delete_criterion(
    criterion_id: uuid.UUID,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
) -> Response:
    EvaluationService.delete_criterion(db, criterion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Đánh giá ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[EvaluationRead], summary="Danh sách đánh giá theo vai trò")
def list_evaluations(
    member_id: uuid.UUID | None = Query(None, description="Lọc theo thành viên thực tập"),
    status: str | None = Query(None, description="DRAFT hoặc PUBLISHED"),
    evaluation_type: str | None = Query(None, description="PERIODIC hoặc FINAL"),
    current_user: User = Depends(_all_roles),
    db: Session = Depends(get_db),
) -> list[EvaluationRead]:
    """Intern: bản đã công bố của mình. Mentor: Intern mình phụ trách. Admin: tất cả (chỉ đọc)."""
    return EvaluationService.list_evaluations(db, current_user, member_id, status, evaluation_type)


@router.post(
    "",
    response_model=EvaluationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Lập đánh giá nháp (Mentor)",
)
def create_evaluation(
    payload: EvaluationCreate,
    current_user: User = Depends(_mentor_only),
    db: Session = Depends(get_db),
) -> EvaluationRead:
    return EvaluationService.create_evaluation(db, current_user, payload)


@router.get("/{evaluation_id}", response_model=EvaluationRead, summary="Chi tiết đánh giá")
def get_evaluation(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(_all_roles),
    db: Session = Depends(get_db),
) -> EvaluationRead:
    return EvaluationService.get_evaluation(db, current_user, evaluation_id)


@router.put("/{evaluation_id}", response_model=EvaluationRead, summary="Sửa đánh giá nháp (Mentor)")
def update_evaluation(
    evaluation_id: uuid.UUID,
    payload: EvaluationUpdate,
    current_user: User = Depends(_mentor_only),
    db: Session = Depends(get_db),
) -> EvaluationRead:
    return EvaluationService.update_evaluation(db, current_user, evaluation_id, payload)


@router.post(
    "/{evaluation_id}/publish",
    response_model=EvaluationRead,
    summary="Công bố đánh giá cho Intern (Mentor)",
)
def publish_evaluation(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(_mentor_only),
    db: Session = Depends(get_db),
) -> EvaluationRead:
    return EvaluationService.publish_evaluation(db, current_user, evaluation_id)
