import uuid
import uuid as uuid_module
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.errors import ApiError
from app.core.settings import TASK_UPLOAD_DIR
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.task import (
    SubmissionCreate,
    SubmissionRead,
    TaskCommentCreate,
    TaskCommentRead,
    TaskCreate,
    TaskDetailRead,
    TaskRead,
    TaskReviewPayload,
    TaskUpdate,
)
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

# UC-7: chỉ Mentor và Intern. Admin không tham gia quản lý Task.
ALL_TASK_ROLES = [UserRole.MENTOR, UserRole.INTERN]
MENTOR_ONLY = [UserRole.MENTOR]

_ALLOWED_TASK_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "audio/mpeg",
    "audio/wav",
    "application/zip",
    "application/x-zip-compressed",
}
_MAX_TASK_FILE_BYTES = 50 * 1024 * 1024  # 50 MB per file


@router.post("/upload", summary="Tải tệp đính kèm Task (Mentor/Intern)")
async def upload_task_files(
    files: Annotated[list[UploadFile], File(description="Danh sách tệp đính kèm")],
    current_user: User = Depends(require_roles(ALL_TASK_ROLES)),
) -> JSONResponse:
    """Upload tệp để đính kèm vào Task (lúc giao việc) hoặc bài nộp."""
    _ = current_user
    urls: list[str] = []
    for file in files:
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_TASK_MIME:
            raise ApiError(
                415,
                "UNSUPPORTED_FILE_TYPE",
                f"Loại tệp '{content_type}' không được hỗ trợ.",
            )
        data = await file.read()
        if len(data) > _MAX_TASK_FILE_BYTES:
            raise ApiError(
                413,
                "FILE_TOO_LARGE",
                f"Tệp '{file.filename}' vượt quá giới hạn 50 MB.",
            )
        original_name = file.filename or "file"
        ext = ""
        if "." in original_name:
            ext = "." + original_name.rsplit(".", 1)[-1].lower()
        safe_name = f"{uuid_module.uuid4().hex}{ext}"
        dest = TASK_UPLOAD_DIR / safe_name
        dest.write_bytes(data)
        urls.append(f"/api/v1/uploads/tasks/{safe_name}")
    return JSONResponse(content={"urls": urls})


@router.get("", response_model=list[TaskRead])
def list_tasks(
    member_id: uuid.UUID | None = Query(None, alias="member_id"),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    overdue: bool | None = None,
    search: str | None = None,
    internship_id: uuid.UUID | None = Query(None, alias="internship_id"),
    current_user: User = Depends(require_roles(ALL_TASK_ROLES)),
    db: Session = Depends(get_db),
):
    return TaskService.list_tasks(
        db,
        current_user,
        member_id=member_id,
        status_filter=status_filter,
        priority=priority,
        overdue=overdue,
        search=search,
        internship_id=internship_id,
    )


@router.post("", response_model=TaskRead)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(require_roles(MENTOR_ONLY)),
    db: Session = Depends(get_db),
):
    return TaskService.create_task(db, current_user, payload)


@router.get("/{task_id}", response_model=TaskDetailRead)
def get_task_detail(
    task_id: uuid.UUID,
    current_user: User = Depends(require_roles(ALL_TASK_ROLES)),
    db: Session = Depends(get_db),
):
    return TaskService.get_detail(db, current_user, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(require_roles(MENTOR_ONLY)),
    db: Session = Depends(get_db),
):
    return TaskService.update_task(db, current_user, task_id, payload)


@router.delete("/{task_id}", response_model=TaskRead)
def cancel_task(
    task_id: uuid.UUID,
    current_user: User = Depends(require_roles(MENTOR_ONLY)),
    db: Session = Depends(get_db),
):
    return TaskService.cancel_task(db, current_user, task_id)


@router.post("/{task_id}/submit", response_model=SubmissionRead)
def submit_task(
    task_id: uuid.UUID,
    payload: SubmissionCreate,
    current_user: User = Depends(require_roles([UserRole.INTERN])),
    db: Session = Depends(get_db),
):
    return TaskService.submit_task(db, current_user, task_id, payload)


@router.delete("/{task_id}/submission", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    task_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.INTERN])),
    db: Session = Depends(get_db),
) -> Response:
    TaskService.delete_submission(db, current_user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/review", response_model=SubmissionRead)
def review_task(
    task_id: uuid.UUID,
    payload: TaskReviewPayload,
    current_user: User = Depends(require_roles(MENTOR_ONLY)),
    db: Session = Depends(get_db),
):
    return TaskService.review_task(db, current_user, task_id, payload)


@router.get("/{task_id}/comments", response_model=list[TaskCommentRead])
def list_comments(
    task_id: uuid.UUID,
    current_user: User = Depends(require_roles(ALL_TASK_ROLES)),
    db: Session = Depends(get_db),
):
    return TaskService.list_comments(db, current_user, task_id)


@router.post("/{task_id}/comments", response_model=TaskCommentRead)
def add_comment(
    task_id: uuid.UUID,
    payload: TaskCommentCreate,
    current_user: User = Depends(require_roles(ALL_TASK_ROLES)),
    db: Session = Depends(get_db),
):
    return TaskService.add_comment(db, current_user, task_id, payload)
