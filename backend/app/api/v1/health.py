from fastapi import APIRouter
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import get_engine
from app.schemas.health import HealthResponse

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


@router.get("/health/db", response_model=HealthResponse)
def get_db_health() -> HealthResponse:
    """Return database connectivity health probe."""
    settings = get_settings()
    if not settings.database_url:
        return HealthResponse(
            status="unconfigured",
            service="itms-backend",
            environment=settings.environment,
            database="not_configured",
        )
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return HealthResponse(
            status="ok",
            service="itms-backend",
            environment=settings.environment,
            database="connected",
        )
    except Exception as exc:
        return HealthResponse(
            status="degraded",
            service="itms-backend",
            environment=settings.environment,
            database=f"error: {exc.__class__.__name__}",
        )
