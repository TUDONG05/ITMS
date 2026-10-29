import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import InternshipStatus, RequestType, UserRole
from app.models.user import User
from app.schemas.internship import (
    BatchResult,
    BatchReviewPayload,
    InternshipApplicationCreate,
    InternshipApplicationRead,
    InternshipApplicationReview,
    InternshipCreate,
    InternshipDetailRead,
    InternshipMemberCreate,
    InternshipMemberDetailRead,
    InternshipRead,
    InternshipRequestRead,
    InternshipRequestReview,
    InternshipUpdate,
)
from app.services.internship import InternshipService

router = APIRouter(prefix="/internships", tags=["internships"])


@router.get("", response_model=list[InternshipRead])
def list_internships(
    status: InternshipStatus | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InternshipRead]:
    """Retrieve list of internships with optional filters."""
    internships = InternshipService.get_internships(
        db, status_filter=status, search=search, skip=skip, limit=limit
    )
    return [InternshipRead.model_validate(item) for item in internships]


@router.post("", response_model=InternshipRead, status_code=status.HTTP_201_CREATED)
def create_internship(
    payload: InternshipCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipRead:
    """Admin creates a new internship batch."""
    internship = InternshipService.create_internship(db, data=payload, creator_id=current_user.id)
    return InternshipRead.model_validate(internship)


# --- ĐẶT CÁC ROUTE TĨNH / QUẢN LÝ ĐƠN ĐĂNG KÝ VÀ REQUESTS LÊN TRƯỚC BẤT KỲ ROUTE CHỨA {id} NÀO ---


@router.get("/open", response_model=list[InternshipRead])
def list_open_internships(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InternshipRead]:
    """Retrieve all open internship batches available for application."""
    open_batches = InternshipService.get_open_internships(db)
    return [InternshipRead.model_validate(item) for item in open_batches]


@router.get("/my-applications", response_model=list[InternshipApplicationRead])
def list_my_applications(
    current_user: User = Depends(require_roles([UserRole.INTERN])),
    db: Session = Depends(get_db),
) -> list[InternshipApplicationRead]:
    """Intern retrieves all their own internship applications."""
    return InternshipService.get_my_applications(db, intern_id=current_user.id)


@router.get("/applications", response_model=list[InternshipApplicationRead])
def list_internship_applications(
    status: str | None = Query(None, description="Filter: PENDING, APPROVED, REJECTED"),
    internship_id: uuid.UUID | None = Query(None, description="Filter by internship batch ID"),
    search: str | None = Query(None, description="Search by intern name or email"),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> list[InternshipApplicationRead]:
    """Admin retrieves all internship applications with optional filters."""
    return InternshipService.get_applications(
        db, status_filter=status, internship_id=internship_id, search=search
    )


@router.get("/applications/{app_id}", response_model=InternshipApplicationRead)
def get_internship_application(
    app_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipApplicationRead:
    """Admin retrieves details of a specific internship application."""
    return InternshipService.get_application_by_id(db, app_id=app_id)


@router.post("/applications/batch-review", response_model=BatchResult)
def batch_review_applications(
    payload: BatchReviewPayload,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> BatchResult:
    """Admin approves or rejects multiple applications at once."""
    return InternshipService.batch_review_applications(
        db, payload=payload, reviewer_id=current_user.id
    )


@router.post("/applications/approve-all", response_model=BatchResult)
def approve_all_applications(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> BatchResult:
    """Admin approves all pending applications in one click."""
    return InternshipService.approve_all_applications(db, reviewer_id=current_user.id)


@router.patch("/applications/{app_id}/review", response_model=InternshipApplicationRead)
def review_internship_application(
    app_id: uuid.UUID,
    payload: InternshipApplicationReview,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipApplicationRead:
    """Admin approves or rejects an intern's application into an internship."""
    return InternshipService.review_application(
        db, app_id=app_id, payload=payload, reviewer_id=current_user.id
    )


@router.get("/requests", response_model=list[InternshipRequestRead])
def list_internship_requests(
    status: str | None = Query(None, description="Filter: PENDING, APPROVED, REJECTED"),
    type: RequestType | None = Query(None, description="Filter: EXTEND, STOP, COMPLETE"),
    start_date: date | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> list[InternshipRequestRead]:
    """Admin retrieves all internship requests with optional filters."""
    requests = InternshipService.get_requests(
        db,
        status_filter=status,
        type_filter=type,
        start_date=start_date,
        end_date=end_date,
    )
    return [InternshipRequestRead.model_validate(r) for r in requests]


@router.post("/requests/batch-review", response_model=BatchResult)
def batch_review_requests(
    payload: BatchReviewPayload,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> BatchResult:
    """Admin approves or rejects multiple requests at once."""
    return InternshipService.batch_review_requests(db, payload=payload, reviewer_id=current_user.id)


@router.post("/requests/approve-all", response_model=BatchResult)
def approve_all_requests(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> BatchResult:
    """Admin approves all pending requests in one click."""
    return InternshipService.approve_all_requests(db, reviewer_id=current_user.id)


@router.patch("/requests/{request_id}/review", response_model=InternshipRequestRead)
def review_internship_request(
    request_id: uuid.UUID,
    payload: InternshipRequestReview,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipRequestRead:
    """Admin approves or rejects an internship request (extend, stop, complete)."""
    req = InternshipService.review_request(
        db, request_id=request_id, payload=payload, reviewer_id=current_user.id
    )
    return InternshipRequestRead.model_validate(req)


# --- CÁC ROUTE DÙNG ID ---


@router.get("/{id}", response_model=InternshipDetailRead)
def get_internship(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InternshipDetailRead:
    """Retrieve internship details by ID."""
    internship = InternshipService.get_internship_by_id(db, internship_id=id)
    return InternshipDetailRead(
        id=internship.id,
        name=internship.name,
        description=internship.description,
        start_date=internship.start_date,
        end_date=internship.end_date,
        status=internship.status,
        roadmap_id=internship.roadmap_id,
        created_by=internship.created_by,
        created_at=internship.created_at,
        updated_at=internship.updated_at,
        members_count=len(internship.members),
    )


@router.patch("/{id}", response_model=InternshipRead)
def update_internship(
    id: uuid.UUID,
    payload: InternshipUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipRead:
    """Admin updates an internship batch."""
    internship = InternshipService.update_internship(db, internship_id=id, data=payload)
    return InternshipRead.model_validate(internship)


@router.post(
    "/{id}/apply", response_model=InternshipApplicationRead, status_code=status.HTTP_201_CREATED
)
def apply_for_internship(
    id: uuid.UUID,
    payload: InternshipApplicationCreate,
    current_user: User = Depends(require_roles([UserRole.INTERN])),
    db: Session = Depends(get_db),
) -> InternshipApplicationRead:
    """Intern applies to an open internship batch."""
    return InternshipService.apply_internship(
        db, internship_id=id, intern_id=current_user.id, data=payload
    )


@router.get("/{id}/members", response_model=list[InternshipMemberDetailRead])
def list_internship_members(
    id: uuid.UUID,
    search: str | None = Query(None, description="Search by intern name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InternshipMemberDetailRead]:
    """Retrieve all enrolled interns in the specified internship."""
    members = InternshipService.get_members_by_internship(db, internship_id=id, search=search)
    return [InternshipMemberDetailRead.model_validate(member) for member in members]


@router.post(
    "/{id}/members",
    response_model=InternshipMemberDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def add_intern_to_internship(
    id: uuid.UUID,
    payload: InternshipMemberCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipMemberDetailRead:
    """Admin enrolls an intern (DEPRECATED: Returns 403 Forbidden)."""
    member = InternshipService.add_member_to_internship(db, internship_id=id, data=payload)
    return InternshipMemberDetailRead.model_validate(member)
