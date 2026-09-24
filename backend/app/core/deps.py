import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.settings import get_settings
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User


def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """Minimal dependency to resolve current user.

    Supports:
    1. X-User-Id header containing user UUID (convenient for API testing & internal dispatch).
    2. Authorization: Bearer <jwt_or_uuid> header.
    """
    user_id_str: str | None = None
    if x_user_id:
        user_id_str = x_user_id.strip()
    elif authorization and authorization.startswith("Bearer "):
        user_id_str = authorization[7:].strip()

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        try:
            settings = get_settings()
            claims = decode_access_token(
                user_id_str,
                secret=settings.jwt_secret,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
            user_uuid = uuid.UUID(str(claims["sub"]))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user identifier format in credentials",
            )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    return user


def require_roles(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Dependency factory that validates current user's role against allowed roles."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized for this operation",
            )
        return current_user

    return role_checker
