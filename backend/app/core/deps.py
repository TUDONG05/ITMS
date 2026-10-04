import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.service import get_auth_service
from app.core.errors import ApiError
from app.core.settings import get_settings
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User


def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """Xác minh danh tính bằng JWT; header test chỉ dùng ngoài production."""
    settings = get_settings()
    if x_user_id and settings.environment in {"development", "test"}:
        try:
            user_id = uuid.UUID(x_user_id.strip())
        except ValueError:
            raise _invalid_credentials() from None
        user = db.get(User, user_id)
        if user is None:
            raise _invalid_credentials()
        if user.status != UserStatus.ACTIVE:
            raise ApiError(403, "ACCOUNT_LOCKED", "Tài khoản không hoạt động.")
        return user

    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "MISSING_ACCESS_TOKEN", "Cần đăng nhập để truy cập tài nguyên này.")
    token = authorization[7:].strip()
    if not token:
        raise ApiError(401, "MISSING_ACCESS_TOKEN", "Cần đăng nhập để truy cập tài nguyên này.")

    account = get_auth_service().get_account_from_access_token(db, token, settings)
    user = db.get(User, account.id)
    if user is None:
        raise _invalid_credentials()
    return user


def require_roles(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Dependency factory kiểm tra vai trò của người dùng hiện tại."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized for this operation",
            )
        return current_user

    return role_checker


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_ACCESS_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
