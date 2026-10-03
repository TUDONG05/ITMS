import uuid as uuid_module
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.errors import ApiError
from app.core.settings import TRAINING_UPLOAD_DIR
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.training import (
    LearningContentCreate,
    LearningContentRead,
    LearningContentUpdate,
    PhaseCreate,
    PhaseDetailRead,
    PhaseRead,
    PhaseUpdate,
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
    QuizCreate,
    QuizRead,
    QuizUpdate,
    RoadmapCreate,
    RoadmapDetailRead,
    RoadmapRead,
    RoadmapUpdate,
)
from app.services.training import TrainingService

router = APIRouter(prefix="/training", tags=["training"])

_ALLOWED_MIME = {
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
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB per file


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------


@router.post("/upload", summary="Tải lên tệp tài nguyên (Admin)")
async def upload_training_files(
    files: Annotated[list[UploadFile], File(description="Danh sách tệp cần upload")],
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> JSONResponse:
    """Upload one or more resource files. Returns list of accessible URLs."""
    urls: list[str] = []
    for file in files:
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_MIME:
            raise ApiError(
                415,
                "UNSUPPORTED_FILE_TYPE",
                f"Loại tệp '{content_type}' không được hỗ trợ.",
            )
        data = await file.read()
        if len(data) > _MAX_FILE_BYTES:
            raise ApiError(
                413,
                "FILE_TOO_LARGE",
                f"Tệp '{file.filename}' vượt quá giới hạn 50 MB.",
            )
        original_name = file.filename or "file"
        # keep extension from original filename, sanitise
        ext = ""
        if "." in original_name:
            ext = "." + original_name.rsplit(".", 1)[-1].lower()
        safe_name = f"{uuid_module.uuid4().hex}{ext}"
        dest = TRAINING_UPLOAD_DIR / safe_name
        dest.write_bytes(data)
        urls.append(f"/api/v1/uploads/training/{safe_name}")
    return JSONResponse(content={"urls": urls})


# ---------------------------------------------------------------------------
# Roadmaps
# ---------------------------------------------------------------------------


@router.get("/roadmaps", response_model=list[RoadmapRead])
def list_roadmaps(
    search: str | None = Query(None, description="Search by name"),
    status: str | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoadmapRead]:
    """Retrieve list of training roadmaps."""
    roadmaps = TrainingService.get_roadmaps(
        db, search=search, status=status, skip=skip, limit=limit
    )
    result: list[RoadmapRead] = []
    for r in roadmaps:
        count = TrainingService.get_phase_count(db, roadmap_id=r.id)
        rm_data = RoadmapRead.model_validate(r)
        rm_data.phase_count = count
        result.append(rm_data)
    return result


@router.post("/roadmaps", response_model=RoadmapRead, status_code=status.HTTP_201_CREATED)
def create_roadmap(
    payload: RoadmapCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> RoadmapRead:
    """Admin creates a new training roadmap."""
    roadmap = TrainingService.create_roadmap(db, data=payload, creator_id=current_user.id)
    return RoadmapRead.model_validate(roadmap)


@router.get("/roadmaps/{id}", response_model=RoadmapDetailRead)
def get_roadmap(
    id: uuid_module.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapDetailRead:
    """Retrieve roadmap details including phases and contents."""
    roadmap = TrainingService.get_roadmap_by_id(db, roadmap_id=id)
    phases = TrainingService.get_phases(db, roadmap_id=id)

    phase_details: list[PhaseDetailRead] = []
    for phase in phases:
        contents = TrainingService.get_contents(db, phase_id=phase.id)
        quizzes = TrainingService.get_quizzes(db, phase_id=phase.id)
        phase_details.append(
            PhaseDetailRead(
                id=phase.id,
                roadmap_id=phase.roadmap_id,
                name=phase.name,
                description=phase.description,
                order_no=phase.order_no,
                created_at=phase.created_at,
                updated_at=phase.updated_at,
                contents=[LearningContentRead.model_validate(c) for c in contents],
                quiz_count=len(quizzes),
            )
        )

    return RoadmapDetailRead(
        id=roadmap.id,
        name=roadmap.name,
        description=roadmap.description,
        status=roadmap.status,
        created_by=roadmap.created_by,
        created_at=roadmap.created_at,
        updated_at=roadmap.updated_at,
        phases=phase_details,
    )


@router.patch("/roadmaps/{id}", response_model=RoadmapRead)
def update_roadmap(
    id: uuid_module.UUID,
    payload: RoadmapUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> RoadmapRead:
    """Admin updates a training roadmap."""
    roadmap = TrainingService.update_roadmap(db, roadmap_id=id, data=payload)
    return RoadmapRead.model_validate(roadmap)


@router.delete("/roadmaps/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """Admin deletes a training roadmap."""
    TrainingService.delete_roadmap(db, roadmap_id=id)


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------


@router.get("/roadmaps/{id}/phases", response_model=list[PhaseRead])
def list_phases(
    id: uuid_module.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PhaseRead]:
    """Retrieve all phases of a roadmap."""
    phases = TrainingService.get_phases(db, roadmap_id=id)
    return [PhaseRead.model_validate(p) for p in phases]


@router.post("/phases", response_model=PhaseRead, status_code=status.HTTP_201_CREATED)
def create_phase(
    payload: PhaseCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> PhaseRead:
    """Admin creates a phase within a roadmap."""
    phase = TrainingService.create_phase(db, data=payload)
    return PhaseRead.model_validate(phase)


@router.patch("/phases/{id}", response_model=PhaseRead)
def update_phase(
    id: uuid_module.UUID,
    payload: PhaseUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> PhaseRead:
    """Admin updates a phase."""
    phase = TrainingService.update_phase(db, phase_id=id, data=payload)
    return PhaseRead.model_validate(phase)


@router.delete("/phases/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phase(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """Admin deletes a phase."""
    TrainingService.delete_phase(db, phase_id=id)


# ---------------------------------------------------------------------------
# Learning Contents
# ---------------------------------------------------------------------------


@router.get("/phases/{id}/contents", response_model=list[LearningContentRead])
def list_contents(
    id: uuid_module.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LearningContentRead]:
    """Retrieve all learning contents within a phase."""
    contents = TrainingService.get_contents(db, phase_id=id)
    return [LearningContentRead.model_validate(c) for c in contents]


@router.post("/contents", response_model=LearningContentRead, status_code=status.HTTP_201_CREATED)
def create_content(
    payload: LearningContentCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> LearningContentRead:
    """Admin creates a learning content item."""
    content = TrainingService.create_content(db, data=payload)
    return LearningContentRead.model_validate(content)


@router.patch("/contents/{id}", response_model=LearningContentRead)
def update_content(
    id: uuid_module.UUID,
    payload: LearningContentUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> LearningContentRead:
    """Admin updates a learning content item."""
    content = TrainingService.update_content(db, content_id=id, data=payload)
    return LearningContentRead.model_validate(content)


@router.delete("/contents/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """Admin deletes a learning content item."""
    TrainingService.delete_content(db, content_id=id)


# ---------------------------------------------------------------------------
# Quizzes
# ---------------------------------------------------------------------------


@router.get("/phases/{id}/quizzes", response_model=list[QuizRead])
def list_quizzes(
    id: uuid_module.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuizRead]:
    """Retrieve all quizzes for a phase."""
    quizzes = TrainingService.get_quizzes(db, phase_id=id)
    return [QuizRead.model_validate(q) for q in quizzes]


@router.post("/quizzes", response_model=QuizRead, status_code=status.HTTP_201_CREATED)
def create_quiz(
    payload: QuizCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> QuizRead:
    """Admin creates a quiz."""
    quiz = TrainingService.create_quiz(db, data=payload, creator_id=current_user.id)
    return QuizRead.model_validate(quiz)


@router.patch("/quizzes/{id}", response_model=QuizRead)
def update_quiz(
    id: uuid_module.UUID,
    payload: QuizUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> QuizRead:
    """Admin updates a quiz."""
    quiz = TrainingService.update_quiz(db, quiz_id=id, data=payload)
    return QuizRead.model_validate(quiz)


@router.delete("/quizzes/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """Admin deletes a quiz."""
    TrainingService.delete_quiz(db, quiz_id=id)


@router.post("/quizzes/{id}/publish", response_model=QuizRead)
def publish_quiz(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> QuizRead:
    """Admin publishes a quiz (sets status to PUBLISHED)."""
    quiz = TrainingService.publish_quiz(db, quiz_id=id)
    return QuizRead.model_validate(quiz)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


@router.get("/quizzes/{id}/questions", response_model=list[QuestionRead])
def list_questions(
    id: uuid_module.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionRead]:
    """Retrieve all questions for a quiz."""
    questions = TrainingService.get_questions(db, quiz_id=id)
    return [QuestionRead.model_validate(q) for q in questions]


@router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> QuestionRead:
    """Admin creates a question."""
    question = TrainingService.create_question(db, data=payload)
    return QuestionRead.model_validate(question)


@router.patch("/questions/{id}", response_model=QuestionRead)
def update_question(
    id: uuid_module.UUID,
    payload: QuestionUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> QuestionRead:
    """Admin updates a question."""
    question = TrainingService.update_question(db, question_id=id, data=payload)
    return QuestionRead.model_validate(question)


@router.delete("/questions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    id: uuid_module.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """Admin deletes a question."""
    TrainingService.delete_question(db, question_id=id)
