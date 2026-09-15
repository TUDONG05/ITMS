from enum import StrEnum
from fastapi import Depends, HTTPException, status

# 4 Vai trò chuẩn theo SRS M01
class UserRole(StrEnum):
    INTERN = "INTERN"
    MENTOR = "MENTOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

def get_current_user():
    return {"id": "demo-uuid", "role": UserRole.INTERN}

def require_roles(allowed_roles: list[UserRole]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này."
            )
        return current_user
    return role_checker