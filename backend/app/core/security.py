from enum import StrEnum

from fastapi import Depends, Header, HTTPException, status


class UserRole(StrEnum):
    INTERN = "INTERN"
    MENTOR = "MENTOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


def get_current_user(x_user_role: str = Header(default="INTERN")) -> dict:
    role_upper = x_user_role.upper()
    valid_roles = [r.value for r in UserRole]
    if role_upper not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Role không hợp lệ hoặc thiếu thông tin xác thực.",
        )
    return {"id": "user-test-id", "role": role_upper}


def require_roles(allowed_roles: list[UserRole]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return current_user

    return role_checker
