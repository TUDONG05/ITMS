import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import UserRole, UserStatus
from app.models.exam import Quiz, QuizAttempt
from app.models.internship import Internship, InternshipMember, InternshipRoadmap
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.task import Task, TaskAssignee
from app.models.user import User
from app.schemas.dashboard import DashboardMetricRead, DashboardRead, DashboardTaskBreakdownRead


def test_pending_count_uses_registration_applications() -> None:
    from app.models.internship import InternshipApplication
    from app.services.dashboard import DashboardService

    session = get_session_factory()()
    try:
        admin = User(
            email=f"count-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        session.flush()
        cohort = Internship(
            name="Count test",
            start_date=datetime(2026, 1, 1).date(),
            end_date=datetime(2026, 12, 31).date(),
            status="ONGOING",
            created_by=admin.id,
        )
        session.add(cohort)
        session.flush()
        application = InternshipApplication(
            internship_id=cohort.id, intern_id=admin.id, status="APPROVED"
        )
        session.add(application)
        session.flush()

        def pending_count() -> int | str:
            result = DashboardService.build(session, admin, cohort.id)
            return next(m.value for m in result.metrics if m.key == "pending_requests")

        assert pending_count() == 0
        application.status = "PENDING"
        session.flush()
        assert pending_count() == 1
        application.status = "REJECTED"
        session.flush()
        assert pending_count() == 0
    finally:
        session.rollback()
        session.close()


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
            "total_roadmaps",
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
                assignees=[TaskAssignee(internship_member_id=member_one.id)],
                created_by=mentor_one.id,
                title="Mentor one task",
                status="TODO",
            ),
            Task(
                assignees=[TaskAssignee(internship_member_id=member_two.id)],
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
            Task.assignees.any(
                TaskAssignee.internship_member_id.in_([member_one.id, member_two.id])
            )
        ).delete(synchronize_session=False)
        session.query(InternshipMember).filter(
            InternshipMember.id.in_([member_one.id, member_two.id])
        ).delete(synchronize_session=False)
        session.delete(internship)
        for user in users:
            session.delete(user)
        session.commit()
        session.close()


def test_intern_dashboard_progress_percent_matches_completed_item_ratio() -> None:
    session = get_session_factory()()
    suffix = uuid.uuid4().hex
    admin = User(
        email=f"progress-admin-{suffix}@example.com",
        password_hash="hash",
        full_name="Progress Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    intern = User(
        email=f"progress-intern-{suffix}@example.com",
        password_hash="hash",
        full_name="Progress Intern",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    session.add_all([admin, intern])
    session.flush()
    roadmap = Roadmap(
        name=f"Progress roadmap {suffix}", status="ACTIVE", position="BACKEND", created_by=admin.id
    )
    old_roadmap = Roadmap(name=f"Previous roadmap {suffix}", status="ACTIVE", position="BACKEND")
    internship = Internship(
        name=f"Progress internship {suffix}",
        start_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        end_date=datetime(2026, 12, 31, tzinfo=UTC).date(),
        status="ONGOING",
        created_by=admin.id,
    )
    session.add_all([roadmap, old_roadmap, internship])
    session.flush()
    phase = Phase(roadmap_id=roadmap.id, name="Phase", order_no=1)
    old_phase = Phase(roadmap_id=old_roadmap.id, name="Previous Phase", order_no=1)
    member = InternshipMember(
        internship_id=internship.id,
        intern_id=intern.id,
        roadmap_id=roadmap.id,
        position="BACKEND",
    )
    session.add_all(
        [
            phase,
            old_phase,
            member,
            InternshipRoadmap(
                internship_id=internship.id, position="BACKEND", roadmap_id=roadmap.id
            ),
        ]
    )
    session.flush()
    contents = [
        LearningContent(
            phase_id=phase.id, title=f"Content {number}", type="LESSON", order_no=number
        )
        for number in range(1, 4)
    ]
    session.add_all(contents)
    old_content = LearningContent(
        phase_id=old_phase.id, title="Previous content", type="DOCUMENT", order_no=1
    )
    session.add(old_content)
    session.flush()
    quizzes = [
        Quiz(phase_id=item.id, title="Quiz", duration_minutes=30, pass_score=60, status="PUBLISHED")
        for item in [phase, old_phase]
    ]
    session.add_all(quizzes)
    session.flush()
    session.add_all(
        [
            QuizAttempt(
                quiz_id=quiz.id,
                internship_member_id=member.id,
                attempt_no=1,
                submitted_at=datetime.now(UTC),
            )
            for quiz in quizzes
        ]
    )
    session.add_all(
        [
            LearningProgress(
                internship_member_id=member.id,
                content_id=old_content.id,
                status="COMPLETED",
                progress_percent=100,
            ),
            LearningProgress(
                internship_member_id=member.id,
                content_id=contents[0].id,
                status="COMPLETED",
                progress_percent=100,
            ),
            LearningProgress(
                internship_member_id=member.id,
                content_id=contents[1].id,
                status="IN_PROGRESS",
                progress_percent=80,
            ),
            LearningProgress(
                internship_member_id=member.id,
                content_id=contents[2].id,
                status="IN_PROGRESS",
                progress_percent=20,
            ),
        ]
    )
    session.commit()
    try:
        response = TestClient(app).get("/api/v1/dashboard", headers={"X-User-Id": str(intern.id)})
        assert response.status_code == 200
        progress = response.json()["progress"]
        assert progress is not None
        assert progress["total"] == 3
        assert progress["completed"] == 1
        metrics = {item["key"]: item["value"] for item in response.json()["metrics"]}
        assert metrics["completed_quizzes"] == 1
        assert progress["percent"] == round(progress["completed"] / progress["total"] * 100, 2)
        member.position = "BA"
        session.commit()
        mismatched = TestClient(app).get("/api/v1/dashboard", headers={"X-User-Id": str(intern.id)})
        assert mismatched.status_code == 200
        assert mismatched.json()["progress"] is None
        assert (
            next(
                item["value"]
                for item in mismatched.json()["metrics"]
                if item["key"] == "completed_quizzes"
            )
            == 0
        )
    finally:
        session.query(LearningProgress).filter(
            LearningProgress.internship_member_id == member.id
        ).delete(synchronize_session=False)
        session.query(LearningContent).filter(
            LearningContent.phase_id.in_([phase.id, old_phase.id])
        ).delete(synchronize_session=False)
        session.delete(member)
        session.delete(phase)
        session.delete(old_phase)
        session.delete(internship)
        session.delete(roadmap)
        session.delete(old_roadmap)
        session.delete(intern)
        session.delete(admin)
        session.commit()
        session.close()
