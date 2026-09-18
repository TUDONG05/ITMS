import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.models.enums import (
    ContentType,
    DocumentStatus,
    EvaluationStatus,
    EvaluationType,
    ExamAttemptStatus,
    FeedbackStatus,
    InternshipPeriodStatus,
    InternshipStatus,
    LearningProgressStatus,
    LifecycleApprovalDecision,
    LifecycleRequestStatus,
    LifecycleRequestType,
    QuestionDifficulty,
    QuestionType,
    RoadmapStatus,
    TaskPriority,
    TaskStatus,
    UserRole,
    UserStatus,
)
from app.schemas.internship import (
    InternshipBase,
    InternshipPeriodBase,
    InternshipPeriodRead,
    InternshipRead,
)
from app.schemas.user import UserCreate, UserRead


def test_all_27_entities_registered():
    """Verify that exactly 27 tables matching S0-03 are registered in SQLAlchemy metadata."""
    expected_tables = {
        "users",
        "internship_periods",
        "internships",
        "mentor_assignments",
        "roadmaps",
        "roadmap_phases",
        "contents",
        "learning_progress",
        "exams",
        "questions",
        "exam_questions",
        "exam_attempts",
        "attempt_answers",
        "tasks",
        "task_submissions",
        "task_comments",
        "task_status_history",
        "evaluations",
        "lifecycle_requests",
        "lifecycle_approvals",
        "notifications",
        "feedback",
        "audit_logs",
        "documents",
        "document_chunks",
        "conversations",
        "chat_messages",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert len(actual_tables) == 27
    assert actual_tables == expected_tables


def test_core_enums_defined():
    """Verify all 12 core SRS enums plus proposed enums are correctly declared."""
    assert UserRole.INTERN == "INTERN"
    assert UserStatus.ACTIVE == "ACTIVE"
    assert InternshipPeriodStatus.PLANNED == "PLANNED"
    assert InternshipStatus.ACTIVE == "ACTIVE"
    assert RoadmapStatus.PUBLISHED == "PUBLISHED"
    assert ContentType.TEXT == "TEXT"
    assert ExamAttemptStatus.SUBMITTED == "SUBMITTED"
    assert TaskPriority.HIGH == "HIGH"
    assert TaskStatus.COMPLETED == "COMPLETED"
    assert EvaluationType.FINAL == "FINAL"
    assert EvaluationStatus.PUBLISHED == "PUBLISHED"
    assert DocumentStatus.INDEXED == "INDEXED"
    assert LifecycleRequestType.EXTEND == "EXTEND"
    assert LifecycleRequestStatus.PENDING == "PENDING"
    assert LifecycleApprovalDecision.APPROVED == "APPROVED"
    assert FeedbackStatus.PENDING == "PENDING"
    assert QuestionType.SINGLE_CHOICE == "SINGLE_CHOICE"
    assert QuestionDifficulty.EASY == "EASY"
    assert LearningProgressStatus.COMPLETED == "COMPLETED"


def test_user_schemas():
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    user_create = UserCreate(
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        password="secretpassword",
    )
    assert user_create.email == "intern@example.com"

    user_read = UserRead(
        id=user_id,
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert user_read.id == user_id


def test_internship_schemas_validation():
    now = datetime.now(UTC)
    period_id = uuid.uuid4()
    intern_id = uuid.uuid4()
    internship_id = uuid.uuid4()

    # Valid period
    period = InternshipPeriodRead(
        id=period_id,
        name="Internship 2026-Q1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status=InternshipPeriodStatus.ACTIVE,
        created_at=now,
    )
    assert period.name == "Internship 2026-Q1"

    # Invalid period: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipPeriodBase(
            name="Invalid Period",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 1),
        )

    # Valid internship
    internship = InternshipRead(
        id=internship_id,
        intern_id=intern_id,
        period_id=period_id,
        status=InternshipStatus.ACTIVE,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        created_at=now,
        updated_at=now,
    )
    assert internship.status == InternshipStatus.ACTIVE

    # Invalid internship: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipBase(
            intern_id=intern_id,
            period_id=period_id,
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
