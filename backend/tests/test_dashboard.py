import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import UserRole, UserStatus
from app.models.internship import Internship, InternshipMember
from app.models.task import Task
from app.models.user import User
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


def test_admin_receives_empty_dashboard_when_no_data_exists() -> None:
    session = get_session_factory()()
    admin = User(
        email=f"dashboard-admin-{uuid.uuid4().hex}@example.com",
        password_hash="hash",
        full_name="Dashboard Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(admin)
    session.flush()
    empty_internship = Internship(
        name=f"Empty dashboard {uuid.uuid4().hex}",
        start_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 12, 31, tzinfo=UTC).date(),
        status="ONGOING",
        created_by=admin.id,
    )
    session.add(empty_internship)
    session.commit()
    session.refresh(admin)
    try:
        response = TestClient(app).get("/api/v1/dashboard", headers={"X-User-Id": str(admin.id)})
        assert response.status_code == 200
        assert response.json()["role"] == "ADMIN"
        assert isinstance(response.json()["recent_items"], list)
        metric_keys = {metric["key"] for metric in response.json()["metrics"]}
        assert {
            "active_interns",
            "active_mentors",
            "ongoing_internships",
            "pending_requests",
            "total_tasks",
            "published_evaluations",
        } <= metric_keys
        filtered_response = TestClient(app).get(
            "/api/v1/dashboard",
            headers={"X-User-Id": str(admin.id)},
            params={"internship_id": str(empty_internship.id)},
        )
        filtered_metrics = {
            metric["key"]: metric["value"] for metric in filtered_response.json()["metrics"]
        }
        assert filtered_response.status_code == 200
        assert filtered_response.json()["recent_items"] == []
        assert filtered_metrics["total_tasks"] == 0
        assert filtered_metrics["pending_requests"] == 0
    finally:
        session.delete(empty_internship)
        session.delete(admin)
        session.commit()
        session.close()


def test_dashboard_scopes_tasks_to_the_authenticated_mentor_and_intern() -> None:
    session = get_session_factory()()
    suffix = uuid.uuid4().hex
    users = [
        User(
            email=f"admin-{suffix}@example.com",
            password_hash="hash",
            full_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        ),
        User(
            email=f"mentor-one-{suffix}@example.com",
            password_hash="hash",
            full_name="Mentor One",
            role=UserRole.MENTOR,
            status=UserStatus.ACTIVE,
        ),
        User(
            email=f"mentor-two-{suffix}@example.com",
            password_hash="hash",
            full_name="Mentor Two",
            role=UserRole.MENTOR,
            status=UserStatus.ACTIVE,
        ),
        User(
            email=f"intern-one-{suffix}@example.com",
            password_hash="hash",
            full_name="Intern One",
            role=UserRole.INTERN,
            status=UserStatus.ACTIVE,
        ),
        User(
            email=f"intern-two-{suffix}@example.com",
            password_hash="hash",
            full_name="Intern Two",
            role=UserRole.INTERN,
            status=UserStatus.ACTIVE,
        ),
    ]
    admin, mentor_one, mentor_two, intern_one, intern_two = users
    session.add_all(users)
    session.flush()
    internship = Internship(
        name=f"Dashboard scope {suffix}",
        start_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 12, 31, tzinfo=UTC).date(),
        status="ONGOING",
        created_by=admin.id,
    )
    session.add(internship)
    session.flush()
    member_one = InternshipMember(
        internship_id=internship.id, intern_id=intern_one.id, mentor_id=mentor_one.id
    )
    member_two = InternshipMember(
        internship_id=internship.id, intern_id=intern_two.id, mentor_id=mentor_two.id
    )
    session.add_all([member_one, member_two])
    session.flush()
    session.add_all(
        [
            Task(
                internship_member_id=member_one.id,
                created_by=mentor_one.id,
                title="Mentor one task",
                status="TODO",
            ),
            Task(
                internship_member_id=member_two.id,
                created_by=mentor_two.id,
                title="Mentor two task",
                status="TODO",
            ),
        ]
    )
    session.commit()
    try:
        client = TestClient(app)
        mentor_response = client.get("/api/v1/dashboard", headers={"X-User-Id": str(mentor_one.id)})
        intern_response = client.get("/api/v1/dashboard", headers={"X-User-Id": str(intern_one.id)})
        filtered_response = client.get(
            "/api/v1/dashboard",
            headers={"X-User-Id": str(intern_one.id)},
            params={"internship_id": str(internship.id)},
        )
        assert mentor_response.status_code == 200
        assert intern_response.status_code == 200
        assert filtered_response.status_code == 403
        assert mentor_response.json()["recent_items"][0]["title"] == "Mentor one task"
        assert intern_response.json()["recent_items"][0]["title"] == "Mentor one task"
    finally:
        session.query(Task).filter(
            Task.internship_member_id.in_([member_one.id, member_two.id])
        ).delete(synchronize_session=False)
        session.query(InternshipMember).filter(
            InternshipMember.id.in_([member_one.id, member_two.id])
        ).delete(synchronize_session=False)
        session.delete(internship)
        for user in users:
            session.delete(user)
        session.commit()
        session.close()
