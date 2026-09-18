"""Initial database schema for ITMS S0-04

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-17 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("INTERN", "MENTOR", "MANAGER", "ADMIN", name="user_role"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", "LOCKED", name="user_status"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. InternshipPeriods table
    op.create_table(
        "internship_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PLANNED", "ACTIVE", "CLOSED", "CANCELLED", name="internship_period_status"),
            nullable=False,
            server_default="PLANNED",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_internship_periods_dates"),
    )
    op.create_index("ix_internship_periods_name", "internship_periods", ["name"], unique=True)

    # 3. Internships table
    op.create_table(
        "internships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "intern_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internship_periods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PLANNED", "ACTIVE", "EXTENDED", "COMPLETED", "TERMINATED", name="internship_status"
            ),
            nullable=False,
            server_default="PLANNED",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_internships_dates"),
    )
    op.create_index("ix_internships_period_id", "internships", ["period_id"])
    op.create_index("ix_internships_intern_id", "internships", ["intern_id"])
    op.create_index("ix_internships_status", "internships", ["status"])
    op.create_index(
        "uq_internships_active_intern",
        "internships",
        ["intern_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # 4. MentorAssignments table
    op.create_table(
        "mentor_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internship_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mentor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR assigned_at <= ended_at", name="ck_mentor_assignments_dates"
        ),
    )
    op.create_index("ix_mentor_assignments_internship_id", "mentor_assignments", ["internship_id"])
    op.create_index("ix_mentor_assignments_mentor_id", "mentor_assignments", ["mentor_id"])
    op.create_index(
        "uq_mentor_assignments_active_primary",
        "mentor_assignments",
        ["internship_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true AND ended_at IS NULL"),
    )

    # 5. Roadmaps table
    op.create_table(
        "roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internship_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="roadmap_status"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_roadmaps_period_id", "roadmaps", ["period_id"])

    # 6. RoadmapPhases table
    op.create_table(
        "roadmap_phases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("completion_rule", sa.Text(), nullable=True),
        sa.UniqueConstraint("roadmap_id", "sequence_no", name="uq_roadmap_phases_sequence"),
        sa.CheckConstraint(
            "duration_days IS NULL OR duration_days > 0", name="ck_roadmap_phases_duration"
        ),
    )
    op.create_index("ix_roadmap_phases_roadmap_id", "roadmap_phases", ["roadmap_id"])

    # 7. Contents table
    op.create_table(
        "contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "phase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmap_phases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "content_type",
            sa.Enum("TEXT", "LINK", "FILE", "VIDEO", name="content_type"),
            nullable=False,
        ),
        sa.Column("content_body", sa.Text(), nullable=True),
        sa.Column("resource_url", sa.String(500), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("phase_id", "sequence_no", name="uq_contents_sequence"),
        sa.CheckConstraint(
            "content_type != 'TEXT' OR (content_body IS NOT NULL AND content_body != '')",
            name="ck_contents_text_body",
        ),
    )
    op.create_index("ix_contents_phase_id", "contents", ["phase_id"])

    # 8. LearningProgress table
    op.create_table(
        "learning_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "intern_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("NOT_STARTED", "IN_PROGRESS", "COMPLETED", name="learning_progress_status"),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("intern_id", "content_id", name="uq_learning_progress_intern_content"),
    )
    op.create_index("ix_learning_progress_intern_id", "learning_progress", ["intern_id"])
    op.create_index("ix_learning_progress_content_id", "learning_progress", ["content_id"])

    # 9. Exams table
    op.create_table(
        "exams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "phase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmap_phases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("passing_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("open_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("duration_minutes > 0", name="ck_exams_duration"),
        sa.CheckConstraint("max_attempts > 0", name="ck_exams_attempts"),
        sa.CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100", name="ck_exams_passing_score"
        ),
        sa.CheckConstraint("close_at > open_at", name="ck_exams_dates"),
    )
    op.create_index("ix_exams_phase_id", "exams", ["phase_id"])

    # 10. Questions table
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "question_type",
            sa.Enum("SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", name="question_type"),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum("EASY", "MEDIUM", "HARD", name="question_difficulty"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("correct_answer", sa.Text(), nullable=False),
    )

    # 11. ExamQuestions table
    op.create_table(
        "exam_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exam_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_questions_exam_question"),
        sa.UniqueConstraint("exam_id", "order_no", name="uq_exam_questions_order"),
    )
    op.create_index("ix_exam_questions_exam_id", "exam_questions", ["exam_id"])
    op.create_index("ix_exam_questions_question_id", "exam_questions", ["question_id"])

    # 12. ExamAttempts table
    op.create_table(
        "exam_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exam_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intern_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("IN_PROGRESS", "SUBMITTED", "GRADED", "EXPIRED", name="exam_attempt_status"),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.UniqueConstraint("exam_id", "intern_id", "attempt_no", name="uq_exam_attempts_no"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="ck_exam_attempts_score"
        ),
    )
    op.create_index("ix_exam_attempts_exam_id", "exam_attempts", ["exam_id"])
    op.create_index("ix_exam_attempts_intern_id", "exam_attempts", ["intern_id"])

    # 13. AttemptAnswers table
    op.create_table(
        "attempt_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exam_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_question"),
    )
    op.create_index("ix_attempt_answers_attempt_id", "attempt_answers", ["attempt_id"])
    op.create_index("ix_attempt_answers_question_id", "attempt_answers", ["question_id"])

    # 14. Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internship_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mentor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="task_priority"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ASSIGNED",
                "PENDING_REVIEW",
                "REVISION_REQUIRED",
                "COMPLETED",
                "CANCELLED",
                name="task_status",
            ),
            nullable=False,
            server_default="ASSIGNED",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_tasks_internship_id", "tasks", ["internship_id"])
    op.create_index("ix_tasks_mentor_id", "tasks", ["mentor_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_deadline", "tasks", ["deadline"])

    # 15. TaskSubmissions table
    op.create_table(
        "task_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("attachment_url", sa.String(500), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.UniqueConstraint("task_id", "version_no", name="uq_task_submissions_version"),
        sa.CheckConstraint(
            "content IS NOT NULL OR link IS NOT NULL OR attachment_url IS NOT NULL",
            name="ck_task_submissions_content",
        ),
    )
    op.create_index("ix_task_submissions_task_id", "task_submissions", ["task_id"])

    # 16. TaskComments table
    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])
    op.create_index("ix_task_comments_author_id", "task_comments", ["author_id"])

    # 17. TaskStatusHistory table
    op.create_table(
        "task_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "old_status",
            postgresql.ENUM(name="task_status", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            postgresql.ENUM(name="task_status", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_task_status_history_task_id", "task_status_history", ["task_id"])

    # 18. Evaluations table
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internship_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_type",
            sa.Enum("PERIODIC", "FINAL", name="evaluation_type"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", name="evaluation_status"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_evaluations_score"),
        sa.CheckConstraint(
            "status != 'PUBLISHED' OR published_at IS NOT NULL", name="ck_evaluations_published_at"
        ),
    )
    op.create_index("ix_evaluations_internship_id", "evaluations", ["internship_id"])
    op.create_index("ix_evaluations_evaluator_id", "evaluations", ["evaluator_id"])

    # 19. Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reference_type", sa.String(100), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index(
        "ix_notifications_recipient_created", "notifications", ["recipient_id", "created_at"]
    )

    # 20. LifecycleRequests table
    op.create_table(
        "lifecycle_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internship_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "request_type",
            sa.Enum("EXTEND", "TERMINATE", "COMPLETE", name="lifecycle_request_type"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="lifecycle_request_status"),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.create_index("ix_lifecycle_requests_internship_id", "lifecycle_requests", ["internship_id"])
    op.create_index("ix_lifecycle_requests_status", "lifecycle_requests", ["status"])
    op.create_index(
        "uq_lifecycle_requests_pending",
        "lifecycle_requests",
        ["internship_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    # 21. LifecycleApprovals table
    op.create_table(
        "lifecycle_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lifecycle_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.Enum("APPROVED", "REJECTED", name="lifecycle_approval_decision"),
            nullable=False,
        ),
        sa.Column(
            "decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_lifecycle_approvals_request_id", "lifecycle_approvals", ["request_id"])
    op.create_index("ix_lifecycle_approvals_approver_id", "lifecycle_approvals", ["approver_id"])

    # 22. Feedback table
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "RESOLVED", "REJECTED", name="feedback_status"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("response", sa.Text(), nullable=True),
    )
    op.create_index("ix_feedback_sender_id", "feedback", ["sender_id"])
    op.create_index("ix_feedback_status", "feedback", ["status"])

    # 23. AuditLogs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # 24. Documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("access_scope", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "INDEXED", "FAILED", "ARCHIVED", name="document_status"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # 25. DocumentChunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_no", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("vector", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("access_scope", sa.String(100), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_no", name="uq_document_chunks_no"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # 26. Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # 27. ChatMessages table
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_type",
            sa.Enum("USER", "ASSISTANT", "SYSTEM", name="chat_message_sender_type"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("chat_messages")
    op.drop_table("conversations")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("audit_logs")
    op.drop_table("feedback")
    op.drop_table("lifecycle_approvals")
    op.drop_table("lifecycle_requests")
    op.drop_table("notifications")
    op.drop_table("evaluations")
    op.drop_table("task_status_history")
    op.drop_table("task_comments")
    op.drop_table("task_submissions")
    op.drop_table("tasks")
    op.drop_table("attempt_answers")
    op.drop_table("exam_attempts")
    op.drop_table("exam_questions")
    op.drop_table("questions")
    op.drop_table("exams")
    op.drop_table("learning_progress")
    op.drop_table("contents")
    op.drop_table("roadmap_phases")
    op.drop_table("roadmaps")
    op.drop_table("mentor_assignments")
    op.drop_table("internships")
    op.drop_table("internship_periods")
    op.drop_table("users")

    # Drop custom enum types created in PostgreSQL
    op.execute("DROP TYPE IF EXISTS chat_message_sender_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS document_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS feedback_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS lifecycle_approval_decision CASCADE;")
    op.execute("DROP TYPE IF EXISTS lifecycle_request_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS lifecycle_request_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS evaluation_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS evaluation_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS task_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS task_priority CASCADE;")
    op.execute("DROP TYPE IF EXISTS exam_attempt_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS question_difficulty CASCADE;")
    op.execute("DROP TYPE IF EXISTS question_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS learning_progress_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS content_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS roadmap_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS internship_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS internship_period_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_role CASCADE;")
