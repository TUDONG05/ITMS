import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.models.exam import Quiz, QuizAttempt
from app.models.interaction import Notification
from app.models.internship import Internship, InternshipMember
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.user import User


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mentor_test_data() -> Generator[dict[str, User | Internship | InternshipMember]]:
    factory = get_session_factory()
    session = factory()

    suffix = uuid.uuid4().hex[:8]

    # Create users
    admin = User(
        email=f"admin_{suffix}@example.com",
        password_hash="hash",
        full_name="Admin Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    mentor_a = User(
        email=f"mentor_a_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Alice",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_b = User(
        email=f"mentor_b_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Bob",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_c = User(
        email=f"mentor_c_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Charlie",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern_a = User(
        email=f"intern_a_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Alex",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_b = User(
        email=f"intern_b_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Ben",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_unassigned = User(
        email=f"intern_un_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Unassigned",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )

    session.add_all([admin, mentor_a, mentor_b, mentor_c, intern_a, intern_b, intern_unassigned])
    session.commit()

    # Create Internship
    internship = Internship(
        name=f"Batch {suffix}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipStatus.ONGOING,
        created_by=admin.id,
    )
    session.add(internship)
    session.commit()

    # Create Roadmap, Phase, Content
    roadmap = Roadmap(
        name=f"Roadmap Backend {suffix}",
        description="Backend Developer Track",
        status="ACTIVE",
        created_by=admin.id,
    )
    session.add(roadmap)
    session.commit()

    phase = Phase(
        roadmap_id=roadmap.id,
        name="Phase 1: Python & FastAPI",
        description="Core FastAPI concepts",
        order_no=1,
    )
    session.add(phase)
    session.commit()

    content = LearningContent(
        phase_id=phase.id,
        title="1. Introduction to Dependency Injection",
        type="LESSON",
        order_no=1,
    )
    session.add(content)
    session.commit()

    # Create Quiz
    quiz = Quiz(
        phase_id=phase.id,
        title="FastAPI DI Quiz",
        duration_minutes=20,
        pass_score=75.0,
        max_attempts=3,
        status="PUBLISHED",
    )
    session.add(quiz)
    session.commit()

    # Member A: assigned to Mentor A
    member_a = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_a.id,
        mentor_id=mentor_a.id,
        roadmap_id=roadmap.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipMemberStatus.ACTIVE,
    )
    # Member B: assigned to Mentor B
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor_b.id,
        roadmap_id=roadmap.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipMemberStatus.ACTIVE,
    )
    # Member Unassigned
    member_unassigned = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_unassigned.id,
        mentor_id=None,
        roadmap_id=roadmap.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add_all([member_a, member_b, member_unassigned])
    session.commit()

    # Learning Progress for Member A
    progress_a = LearningProgress(
        internship_member_id=member_a.id,
        content_id=content.id,
        status="COMPLETED",
        progress_percent=100.0,
        completed_at=datetime.now(UTC),
    )
    session.add(progress_a)

    # Quiz Attempt for Member A
    attempt_a = QuizAttempt(
        quiz_id=quiz.id,
        internship_member_id=member_a.id,
        attempt_no=1,
        score=85.0,
        passed=True,
        started_at=datetime.now(UTC),
        submitted_at=datetime.now(UTC),
    )
    session.add(attempt_a)
    session.commit()

    data = {
        "admin": admin,
        "mentor_a": mentor_a,
        "mentor_b": mentor_b,
        "mentor_c": mentor_c,
        "intern_a": intern_a,
        "intern_b": intern_b,
        "intern_unassigned": intern_unassigned,
        "internship": internship,
        "roadmap": roadmap,
        "phase": phase,
        "content": content,
        "quiz": quiz,
        "member_a": member_a,
        "member_b": member_b,
        "member_unassigned": member_unassigned,
    }

    yield data

    # Cleanup
    session.rollback()
    session.close()


def test_mentor_gets_own_assigned_interns(client: TestClient, mentor_test_data: dict):
    """1. Mentor can retrieve their own assigned interns list."""
    mentor_a = mentor_test_data["mentor_a"]
    member_a = mentor_test_data["member_a"]

    response = client.get(
        "/api/v1/mentor/interns",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(member_a.id)
    assert data[0]["intern_name"] == "Intern Alex"
    assert data[0]["progress_percent"] == 100.0
    assert data[0]["quizzes_passed"] == 1


def test_mentor_cannot_get_unassigned_interns_in_list(client: TestClient, mentor_test_data: dict):
    """2. Mentor cannot see interns assigned to other mentors in list."""
    mentor_a = mentor_test_data["mentor_a"]
    member_b = mentor_test_data["member_b"]

    response = client.get(
        "/api/v1/mentor/interns",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data]
    assert str(member_b.id) not in ids


def test_mentor_cannot_bypass_via_id_or_params(client: TestClient, mentor_test_data: dict):
    """3. Mentor cannot bypass boundary by passing unassigned intern ID in URL or query."""
    mentor_a = mentor_test_data["mentor_a"]
    member_b = mentor_test_data["member_b"]
    intern_b = mentor_test_data["intern_b"]

    # Try accessing by member_b id
    resp_by_member = client.get(
        f"/api/v1/mentor/interns/{member_b.id}",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert resp_by_member.status_code == 403
    assert "not assigned" in resp_by_member.json()["detail"].lower()

    # Try accessing by intern_b user id
    resp_by_user = client.get(
        f"/api/v1/mentor/interns/{intern_b.id}",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert resp_by_user.status_code == 403


def test_search_and_filter_respects_mentor_boundary(client: TestClient, mentor_test_data: dict):
    """4. Search & filter only returns data within the mentor's assignment scope."""
    mentor_a = mentor_test_data["mentor_a"]

    # Mentor A searches for "Ben" (who is assigned to Mentor B)
    response = client.get(
        "/api/v1/mentor/interns?search=Ben",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response.status_code == 200
    assert response.json() == []

    # Mentor A searches for "Alex" (assigned to Mentor A)
    response_alex = client.get(
        "/api/v1/mentor/interns?search=Alex",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response_alex.status_code == 200
    assert len(response_alex.json()) == 1


def test_mentor_views_detail_of_assigned_intern(client: TestClient, mentor_test_data: dict):
    """5. Mentor can view full details of an assigned intern (profile, roadmap, quiz, history)."""
    mentor_a = mentor_test_data["mentor_a"]
    member_a = mentor_test_data["member_a"]

    response = client.get(
        f"/api/v1/mentor/interns/{member_a.id}",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intern"]["full_name"] == "Intern Alex"
    assert data["roadmap"]["roadmap_name"] is not None
    assert len(data["roadmap"]["phases"]) > 0
    assert len(data["quiz_attempts"]) == 1
    assert data["quiz_attempts"][0]["score"] == 85.0
    assert data["quiz_attempts"][0]["passed"] is True


def test_mentor_cannot_view_detail_of_unassigned_intern(client: TestClient, mentor_test_data: dict):
    """6. Mentor cannot view detail of an intern outside their scope (403 Forbidden)."""
    mentor_b = mentor_test_data["mentor_b"]
    member_a = mentor_test_data["member_a"]

    response = client.get(
        f"/api/v1/mentor/interns/{member_a.id}",
        headers={"X-User-Id": str(mentor_b.id)},
    )
    assert response.status_code == 403


def test_admin_assigns_primary_mentor(client: TestClient, mentor_test_data: dict):
    """7. Admin assigns a primary mentor to an unassigned intern."""
    admin = mentor_test_data["admin"]
    mentor_c = mentor_test_data["mentor_c"]
    member_unassigned = mentor_test_data["member_unassigned"]

    response = client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(admin.id)},
        json={
            "member_id": str(member_unassigned.id),
            "mentor_id": str(mentor_c.id),
            "note": "Initial primary mentor assignment",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASSIGN"
    assert data["new_mentor_id"] == str(mentor_c.id)
    assert data["old_mentor_id"] is None
    assert data["note"] == "Initial primary mentor assignment"


def test_admin_changes_primary_mentor(client: TestClient, mentor_test_data: dict):
    """8. Admin changes the primary mentor of an intern to a new mentor."""
    admin = mentor_test_data["admin"]
    mentor_a = mentor_test_data["mentor_a"]
    mentor_c = mentor_test_data["mentor_c"]
    member_a = mentor_test_data["member_a"]

    # Reassign member_a from mentor_a to mentor_c
    response = client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(admin.id)},
        json={
            "member_id": str(member_a.id),
            "mentor_id": str(mentor_c.id),
            "note": "Reassigned for specialized Python track",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "CHANGE"
    assert data["old_mentor_id"] == str(mentor_a.id)
    assert data["new_mentor_id"] == str(mentor_c.id)


def test_assignment_history_is_recorded_and_queried(client: TestClient, mentor_test_data: dict):
    """9. Mentor assignment history is recorded in database and queryable with full audit fields."""
    admin = mentor_test_data["admin"]
    mentor_a = mentor_test_data["mentor_a"]
    mentor_b = mentor_test_data["mentor_b"]
    member_unassigned = mentor_test_data["member_unassigned"]

    # First assign
    client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(admin.id)},
        json={
            "member_id": str(member_unassigned.id),
            "mentor_id": str(mentor_a.id),
            "note": "First assignment",
        },
    )

    # Then change
    client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(admin.id)},
        json={
            "member_id": str(member_unassigned.id),
            "mentor_id": str(mentor_b.id),
            "note": "Changed to Mentor B",
        },
    )

    # Query history
    hist_resp = client.get(
        f"/api/v1/mentor/assignments/history?member_id={member_unassigned.id}",
        headers={"X-User-Id": str(admin.id)},
    )
    assert hist_resp.status_code == 200
    records = hist_resp.json()
    assert len(records) >= 2
    # Verify audit attributes
    latest = records[0]
    assert latest["intern_name"] == "Intern Unassigned"
    assert latest["changed_by_name"] == "Admin Test"
    assert "changed_at" in latest
    assert latest["action"] in ["ASSIGN", "CHANGE"]

    # Verify directly in database table thong_bao
    factory = get_session_factory()
    with factory() as db:
        notifications = (
            db.query(Notification)
            .filter(Notification.title.in_(["MENTOR_ASSIGN", "MENTOR_CHANGE"]))
            .all()
        )
        assert len(notifications) >= 2


def test_permission_checks_for_assignment_apis(client: TestClient, mentor_test_data: dict):
    """10. Permission checks: Interns or unauthorized users cannot assign or change mentors."""
    intern_a = mentor_test_data["intern_a"]
    mentor_a = mentor_test_data["mentor_a"]
    mentor_b = mentor_test_data["mentor_b"]
    member_b = mentor_test_data["member_b"]

    # Intern tries to assign mentor -> 403 Forbidden
    resp_intern = client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(intern_a.id)},
        json={
            "member_id": str(member_b.id),
            "mentor_id": str(mentor_a.id),
        },
    )
    assert resp_intern.status_code == 403

    # Intern tries to list mentor interns -> 403 Forbidden
    resp_intern_list = client.get(
        "/api/v1/mentor/interns",
        headers={"X-User-Id": str(intern_a.id)},
    )
    assert resp_intern_list.status_code == 403

    # Intern tries to view mentor overview -> 403 Forbidden
    resp_intern_overview = client.get(
        "/api/v1/mentor/overview",
        headers={"X-User-Id": str(intern_a.id)},
    )
    assert resp_intern_overview.status_code == 403

    # Mentor A tries to reassign Mentor B's intern -> 403 Forbidden
    resp_mentor_cross = client.post(
        "/api/v1/mentor/assignments",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_b.id),
            "mentor_id": str(mentor_a.id),
        },
    )
    assert resp_mentor_cross.status_code == 403

    # Unauthenticated request -> 401 Unauthorized
    resp_unauth = client.post(
        "/api/v1/mentor/assignments",
        json={
            "member_id": str(member_b.id),
            "mentor_id": str(mentor_a.id),
        },
    )
    assert resp_unauth.status_code == 401


def test_mentor_overview_metrics(client: TestClient, mentor_test_data: dict):
    """11. Mentor overview aggregates real metrics for the current mentor."""
    mentor_a = mentor_test_data["mentor_a"]

    response = client.get(
        "/api/v1/mentor/overview",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_interns"] >= 1
    assert data["active_interns"] >= 1
    assert data["avg_progress"] >= 0.0
    assert len(data["recent_interns"]) >= 1
