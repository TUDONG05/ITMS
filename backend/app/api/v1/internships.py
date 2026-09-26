import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import InternshipStatus, UserRole
from app.models.user import User
from app.schemas.internship import (
    InternshipCreate,
    InternshipDetailRead,
    InternshipMemberCreate,
    InternshipMemberDetailRead,
    InternshipRead,
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


@router.get("/{id}/members", response_model=list[InternshipMemberDetailRead])
def list_internship_members(
    id: uuid.UUID,
    search: str | None = Query(None, description="Search by intern name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InternshipMemberDetailRead]:
    """Retrieve all enrolled interns in the specified internship."""
    members = InternshipService.get_members_by_internship(
        db, internship_id=id, search=search
    )
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
    """Admin enrolls an intern into the specified internship."""
    member = InternshipService.add_member_to_internship(db, internship_id=id, data=payload)
    return InternshipMemberDetailRead.model_validate(member)
