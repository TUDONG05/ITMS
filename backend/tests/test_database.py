import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.models.enums import (
    AIMessageRole,
    ContentType,
    CriteriaStatus,
    EvaluationStatus,
    EvaluationType,
    InternshipRequestStatus,
    InternshipRequestType,
    InternshipStatus,
    LearningProgressStatus,
    MemberStatus,
    QuestionType,
    QuizStatus,
    RoadmapStatus,
    SubmissionStatus,
    TargetType,
    TaskPriority,
    TaskStatus,
    UserRole,
    UserStatus,
)
from app.schemas.internship import (
    InternshipBase,
    InternshipMemberBase,
    InternshipMemberRead,
    InternshipRead,
)
from app.schemas.user import UserCreate, UserRead


def test_all_20_entities_registered():
    """Verify that exactly 20 tables matching diagram.pdf are registered in SQLAlchemy metadata."""
    expected_tables = {
        "users",
        "internships",
        "roadmaps",
        "internship_members",
        "phases",
        "learning_contents",
        "learning_progress",
        "quizzes",
        "questions",
        "quiz_attempts",
        "tasks",
        "task_submissions",
        "task_comments",
        "evaluation_criteria",
        "evaluations",
        "internship_requests",
        "notifications",
        "notification_reads",
        "ai_conversations",
        "ai_messages",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert len(actual_tables) == 20
    assert actual_tables == expected_tables


def test_core_enums_defined():
    """Verify all 20-table schema enums matching migration are correctly declared."""
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.MENTOR == "MENTOR"
    assert UserRole.INTERN == "INTERN"
    assert UserStatus.ACTIVE == "ACTIVE"
    assert InternshipStatus.DRAFT == "DRAFT"
    assert InternshipStatus.OPEN == "OPEN"
    assert InternshipStatus.ONGOING == "ONGOING"
    assert InternshipStatus.COMPLETED == "COMPLETED"
    assert InternshipStatus.CANCELLED == "CANCELLED"
    assert MemberStatus.ACTIVE == "ACTIVE"
    assert MemberStatus.EXTENDED == "EXTENDED"
    assert MemberStatus.STOPPED == "STOPPED"
    assert MemberStatus.COMPLETED == "COMPLETED"
    assert RoadmapStatus.ACTIVE == "ACTIVE"
    assert ContentType.LESSON == "LESSON"
    assert LearningProgressStatus.COMPLETED == "COMPLETED"
    assert QuizStatus.DRAFT == "DRAFT"
    assert QuestionType.SINGLE_CHOICE == "SINGLE_CHOICE"
    assert TaskPriority.HIGH == "HIGH"
    assert TaskStatus.COMPLETED == "COMPLETED"
    assert SubmissionStatus.SUBMITTED == "SUBMITTED"
    assert EvaluationType.FINAL == "FINAL"
    assert EvaluationStatus.PUBLISHED == "PUBLISHED"
    assert CriteriaStatus.ACTIVE == "ACTIVE"
    assert InternshipRequestType.EXTEND == "EXTEND"
    assert InternshipRequestStatus.PENDING == "PENDING"
    assert TargetType.ALL == "ALL"
    assert AIMessageRole.USER == "USER"


def test_user_schemas():
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    user_create = UserCreate(
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        password="secretpassword",
        phone="0912345678",
        avatar_url="https://example.com/avatar.png",
    )
    assert user_create.email == "intern@example.com"
    assert user_create.phone == "0912345678"

    user_read = UserRead(
        id=user_id,
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
        phone="0912345678",
        avatar_url="https://example.com/avatar.png",
        created_at=now,
        updated_at=now,
    )
    assert user_read.id == user_id
    assert user_read.avatar_url == "https://example.com/avatar.png"


def test_internship_schemas_validation():
    now = datetime.now(UTC)
    internship_id = uuid.uuid4()
    member_id = uuid.uuid4()
    intern_id = uuid.uuid4()

    # Valid internship
    internship = InternshipRead(
        id=internship_id,
        name="Internship 2026-Q1",
        description="Spring batch",
        status=InternshipStatus.DRAFT,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        created_at=now,
        updated_at=now,
    )
    assert internship.name == "Internship 2026-Q1"
    assert internship.status == InternshipStatus.DRAFT

    # Invalid internship: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipBase(
            name="Invalid Batch",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 1),
        )

    # Valid internship member
    member = InternshipMemberRead(
        id=member_id,
        internship_id=internship_id,
        intern_id=intern_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status=MemberStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert member.status == MemberStatus.ACTIVE

    # Invalid internship member: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipMemberBase(
            internship_id=internship_id,
            intern_id=intern_id,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )


def test_health_endpoints():
    client = TestClient(app)

    # Legacy probe
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "itms-backend"

    # Database connectivity probe
    resp_db = client.get("/api/v1/health/db")
    assert resp_db.status_code == 200
    db_data = resp_db.json()
    assert db_data["service"] == "itms-backend"
    assert "database" in db_data
