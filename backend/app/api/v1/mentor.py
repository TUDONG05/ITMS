import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.mentor import (
    InternRoadmapDetailSchema,
    MentorAssignmentHistoryItem,
    MentorAssignRequestPayload,
    MentorInternDetailSchema,
    MentorInternListItem,
    MentorOverviewMetricsSchema,
    QuizAttemptDetailSchema,
)
from app.services.mentor import MentorService

router = APIRouter(prefix="/mentor", tags=["mentor"])


@router.get("/overview", response_model=MentorOverviewMetricsSchema)
def get_mentor_overview(
    current_user: User = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> MentorOverviewMetricsSchema:
    """Retrieve overview metrics and KPIs for the logged-in mentor."""
    return MentorService.get_mentor_overview(db, current_user=current_user)


@router.get("/interns", response_model=list[MentorInternListItem])
def get_mentor_interns(
    search: str | None = Query(None, description="Search by name or email"),
    status: str | None = Query(None, description="Filter by status (ACTIVE, COMPLETED, etc.)"),
    internship_id: uuid.UUID | None = Query(None, description="Filter by internship ID"),
    current_user: User = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> list[MentorInternListItem]:
    """List interns assigned to the current mentor with search and filters."""
    return MentorService.get_mentor_interns(
        db,
        current_user=current_user,
        search=search,
        status_filter=status,
        internship_id=internship_id,
    )


@router.get("/interns/{member_id}", response_model=MentorInternDetailSchema)
def get_intern_detail(
    member_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> MentorInternDetailSchema:
    """Retrieve complete profile, roadmap, quizzes, and history of an intern."""
    return MentorService.get_intern_detail(
        db, member_id_or_intern_id=member_id, current_user=current_user
    )


@router.get("/interns/{member_id}/roadmap", response_model=InternRoadmapDetailSchema)
def get_intern_roadmap(
    member_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> InternRoadmapDetailSchema:
    """Retrieve detailed roadmap and learning progress of an intern."""
    member = MentorService._find_member(db, member_id)
    if not member:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship member not found",
        )
    MentorService._assert_mentor_access(current_user, member)
    return MentorService.get_intern_roadmap(db, member=member)


@router.get("/interns/{member_id}/quizzes", response_model=list[QuizAttemptDetailSchema])
def get_intern_quizzes(
    member_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> list[QuizAttemptDetailSchema]:
    """Retrieve quiz attempts and scores of an intern."""
    member = MentorService._find_member(db, member_id)
    if not member:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship member not found",
        )
    MentorService._assert_mentor_access(current_user, member)
    return MentorService.get_intern_quizzes(db, member=member)


@router.post("/assignments", response_model=MentorAssignmentHistoryItem)
def assign_or_change_mentor(
    payload: MentorAssignRequestPayload,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR])),
    db: Session = Depends(get_db),
) -> MentorAssignmentHistoryItem:
    """Assign or change primary mentor for an intern and record audit trail."""
    return MentorService.assign_or_change_mentor(
        db, payload=payload, current_user=current_user
    )


@router.get("/assignments/history", response_model=list[MentorAssignmentHistoryItem])
def get_assignment_history(
    member_id: uuid.UUID | None = Query(None, description="Filter history by member ID"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR])),
    db: Session = Depends(get_db),
) -> list[MentorAssignmentHistoryItem]:
    """Retrieve mentor assignment and change history with full audit trail."""
    return MentorService.get_assignment_history(
        db, current_user=current_user, member_id=member_id
    )
