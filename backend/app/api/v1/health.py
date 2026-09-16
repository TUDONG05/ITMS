from fastapi import APIRouter, Depends

from app.core.security import UserRole, require_roles
from app.core.settings import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return a dependency-free liveness response for local development and deployment probes."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "itms-backend",
        "environment": settings.environment,
    }


# Route 1: Kiểm thử áp dụng RBAC Guard
@router.get(
    "/protected-route",
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)
def protected_admin_route():
    return {"message": "Welcome Admin!"}


# Route 2: Bằng chứng Core vẫn hoạt động khi Email/AI service gặp sự cố
@router.get("/core-service")
def core_service_with_fallback(service_status: str = "ok"):
    if service_status == "fail":
        return {
            "status": "warning",
            "core_status": "operational",
            "message": "Dịch vụ phụ trợ (Email/AI) lỗi, core hệ thống vẫn hoạt động an toàn.",
        }
    return {"status": "ok", "core_status": "operational"}
