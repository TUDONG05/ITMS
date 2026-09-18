from app.schemas.base import BaseSchema


class HealthResponse(BaseSchema):
    status: str
    service: str
    environment: str
    database: str | None = None
