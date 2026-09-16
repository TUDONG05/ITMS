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


@router.get(
    "/protected-route",
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)
def protected_admin_route() -> dict[str, str]:
    return {"message": "Welcome Admin!"}
