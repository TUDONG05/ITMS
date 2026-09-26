import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.internship import (
    InternshipMemberDetailRead,
    InternshipMemberUpdate,
    MentorAssignRequest,
)
from app.services.internship import InternshipService

router = APIRouter(prefix="/internship-members", tags=["internship-members"])


@router.get("/{member_id}", response_model=InternshipMemberDetailRead)
def get_internship_member(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InternshipMemberDetailRead:
    """Retrieve details of a single internship member."""
    member = InternshipService.get_member_by_id(db, member_id=member_id)
    return InternshipMemberDetailRead.model_validate(member)



@router.patch("/{member_id}", response_model=InternshipMemberDetailRead)
def update_internship_member(
    member_id: uuid.UUID,
    payload: InternshipMemberUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipMemberDetailRead:
    """Admin updates internship member status, dates, and/or mentor."""
    member = InternshipService.update_member(
        db, member_id=member_id, payload=payload
    )
    return InternshipMemberDetailRead.model_validate(member)


@router.patch("/{member_id}/mentor", response_model=InternshipMemberDetailRead)
def assign_or_change_mentor(
    member_id: uuid.UUID,
    payload: MentorAssignRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternshipMemberDetailRead:
    """Admin assigns or updates the mentor for an enrolled intern."""
    member = InternshipService.assign_mentor_to_member(
        db, member_id=member_id, mentor_id=payload.mentor_id
    )
    return InternshipMemberDetailRead.model_validate(member)
