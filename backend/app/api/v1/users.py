import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserStatusUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    role: UserRole | None = Query(None, description="Filter users by role"),
    status: UserStatus | None = Query(None, description="Filter users by status"),
    search: str | None = Query(None, description="Search by full name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    """Retrieve users list, optionally filtered by role, status, and search query."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.value)
    if status:
        query = query.filter(User.status == status.value)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(User.full_name).like(term) | func.lower(User.email).like(term)
        )
    users = query.order_by(User.full_name).offset(skip).limit(limit).all()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> UserRead:
    """Create a new user. Only Admin is authorized."""
    normalized_email = payload.email.strip().casefold()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng bởi một tài khoản khác.",
        )

    new_user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        status=payload.status.value,
        phone=payload.phone.strip() if payload.phone else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserRead.model_validate(new_user)


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
            detail="Không tìm thấy người dùng.",
        )
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update a user's details and role. Only Admin is authorized."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng.",
        )

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() if payload.phone else None
    if payload.role is not None:
        user.role = payload.role.value

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> UserRead:
    """Lock or unlock a user account. Only Admin is authorized."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng.",
        )

    if user.id == current_user.id and payload.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự khóa tài khoản của chính mình.",
        )

    user.status = payload.status.value
    if payload.status == UserStatus.LOCKED:
        # Invalidate existing JWT access tokens immediately
        user.token_version += 1

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
