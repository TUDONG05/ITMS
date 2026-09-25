import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    role: UserRole | None = Query(None, description="Filter users by role"),
    status: UserStatus | None = Query(None, description="Filter users by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    """Retrieve users list, optionally filtered by role and status."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.value)
    if status:
        query = query.filter(User.status == status.value)
    users = query.order_by(User.full_name).offset(skip).limit(limit).all()
    return [UserRead.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Retrieve a single user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)
