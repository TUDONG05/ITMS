from app.models.enums import UserRole
from app.schemas.dashboard import DashboardMetricRead, DashboardRead, DashboardTaskBreakdownRead


def test_empty_intern_dashboard_schema_serializes() -> None:
    payload = DashboardRead(
        role=UserRole.INTERN,
        metrics=[DashboardMetricRead(key="assigned_tasks", label="Task được giao", value=0)],
        task_breakdown=DashboardTaskBreakdownRead(),
        progress=None,
        recent_items=[],
    )

    assert payload.model_dump(mode="json")["role"] == "INTERN"
    assert payload.model_dump(mode="json")["metrics"][0]["value"] == 0
