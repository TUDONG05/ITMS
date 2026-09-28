from __future__ import annotations

from datetime import datetime

from app.models.enums import UserRole
from app.schemas.base import BaseSchema


class DashboardMetricRead(BaseSchema):
    key: str
    label: str
    value: int | float | str


class DashboardTaskBreakdownRead(BaseSchema):
    todo: int = 0
    in_progress: int = 0
    submitted: int = 0
    revision_required: int = 0
    completed: int = 0
    overdue: int = 0


class DashboardProgressRead(BaseSchema):
    percent: float
    completed: int
    total: int


class DashboardRecentItemRead(BaseSchema):
    title: str
    subtitle: str | None = None
    status: str | None = None
    due_at: datetime | None = None


class DashboardRead(BaseSchema):
    role: UserRole
    metrics: list[DashboardMetricRead]
    task_breakdown: DashboardTaskBreakdownRead
    progress: DashboardProgressRead | None = None
    recent_items: list[DashboardRecentItemRead]
