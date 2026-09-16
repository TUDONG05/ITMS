from enum import StrEnum

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.settings import Settings, get_settings


class UserRole(StrEnum):
    INTERN = "INTERN"
    MENTOR = "MENTOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Thông tin xác thực không hợp lệ.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict[str, str | UserRole]:
    """Authenticate a bearer JWT and derive the caller's role from signed claims."""
    if credentials is None:
        raise _unauthorized()
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured.",
        )

    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss", "role", "sub"]},
        )
        user_id = claims["sub"]
        role = UserRole(claims["role"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise _unauthorized() from None

    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized()
    return {"id": user_id, "role": role}


def require_roles(allowed_roles: list[UserRole]):
    def role_checker(
        current_user: dict[str, str | UserRole] = Depends(get_current_user),
    ) -> dict[str, str | UserRole]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return current_user

    return role_checker
