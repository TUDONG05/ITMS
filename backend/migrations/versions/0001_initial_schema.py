"""Initial 20-table schema for ITMS.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    statements = [
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(20), avatar_url TEXT, role VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', token_version INTEGER NOT NULL DEFAULT 0,
            password_reset_token_hash VARCHAR(255), password_reset_expires_at TIMESTAMPTZ,
            password_changed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_users_role CHECK (role IN ('ADMIN','MENTOR','INTERN')),
            CONSTRAINT ck_users_status CHECK (status IN ('ACTIVE','LOCKED','INACTIVE'))
        )
        """,
        """
        CREATE TABLE internships (
            id UUID PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE, description TEXT,
            start_date DATE NOT NULL, end_date DATE NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_internships_dates CHECK (end_date >= start_date),
            CONSTRAINT ck_internships_status CHECK (status IN ('DRAFT','OPEN','ONGOING','COMPLETED','CANCELLED'))
        )
        """,
        """
        CREATE TABLE roadmaps (
            id UUID PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE, description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_roadmaps_status CHECK (status IN ('DRAFT','ACTIVE','ARCHIVED'))
        )
        """,
        """
        CREATE TABLE phases (
            id UUID PRIMARY KEY, roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL, description TEXT, order_no INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_phases_roadmap_order UNIQUE (roadmap_id, order_no)
        )
        """,
        """
        CREATE TABLE learning_contents (
            id UUID PRIMARY KEY, phase_id UUID NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL, description TEXT, type VARCHAR(20) NOT NULL,
            content TEXT, resource_url TEXT, order_no INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_learning_contents_phase_order UNIQUE (phase_id, order_no),
            CONSTRAINT ck_learning_contents_type CHECK (type IN ('LESSON','DOCUMENT','VIDEO','LINK'))
        )
        """,
        """
        CREATE TABLE internship_members (
            id UUID PRIMARY KEY, internship_id UUID NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
            intern_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            mentor_id UUID REFERENCES users(id) ON DELETE SET NULL,
            roadmap_id UUID REFERENCES roadmaps(id) ON DELETE SET NULL,
            start_date DATE, end_date DATE, status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_internship_members_intern UNIQUE (internship_id, intern_id),
            CONSTRAINT ck_internship_members_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
            CONSTRAINT ck_internship_members_status CHECK (status IN ('ACTIVE','EXTENDED','STOPPED','COMPLETED'))
        )
        """,
        """
        CREATE TABLE internship_requests (
            id UUID PRIMARY KEY, internship_member_id UUID NOT NULL REFERENCES internship_members(id) ON DELETE CASCADE,
            requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            type VARCHAR(20) NOT NULL, reason TEXT NOT NULL, requested_end_date DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING', reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
            review_note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMPTZ,
            CONSTRAINT ck_internship_requests_type CHECK (type IN ('EXTEND','STOP','COMPLETE')),
            CONSTRAINT ck_internship_requests_status CHECK (status IN ('PENDING','APPROVED','REJECTED'))
        )
        """,
        """
        CREATE TABLE learning_progress (
            id UUID PRIMARY KEY, internship_member_id UUID NOT NULL REFERENCES internship_members(id) ON DELETE CASCADE,
            content_id UUID NOT NULL REFERENCES learning_contents(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED', progress_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
            completed_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_learning_progress_member_content UNIQUE (internship_member_id, content_id),
            CONSTRAINT ck_learning_progress_status CHECK (status IN ('NOT_STARTED','IN_PROGRESS','COMPLETED')),
            CONSTRAINT ck_learning_progress_percent CHECK (progress_percent >= 0 AND progress_percent <= 100)
        )
        """,
        """
        CREATE TABLE quizzes (
            id UUID PRIMARY KEY, phase_id UUID NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL, description TEXT, duration_minutes INTEGER NOT NULL,
            pass_score NUMERIC(5,2) NOT NULL, max_attempts INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_quizzes_duration CHECK (duration_minutes > 0),
            CONSTRAINT ck_quizzes_pass_score CHECK (pass_score >= 0 AND pass_score <= 100),
            CONSTRAINT ck_quizzes_max_attempts CHECK (max_attempts > 0),
            CONSTRAINT ck_quizzes_status CHECK (status IN ('DRAFT','PUBLISHED','CLOSED'))
        )
        """,
        """
        CREATE TABLE questions (
            id UUID PRIMARY KEY, quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
            content TEXT NOT NULL, type VARCHAR(30) NOT NULL, options JSONB,
            correct_answer JSONB NOT NULL, score NUMERIC(5,2) NOT NULL, order_no INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_questions_type CHECK (type IN ('SINGLE_CHOICE','MULTIPLE_CHOICE','TRUE_FALSE','TEXT'))
        )
        """,
        """
        CREATE TABLE quiz_attempts (
            id UUID PRIMARY KEY, quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
            internship_member_id UUID NOT NULL REFERENCES internship_members(id) ON DELETE CASCADE,
            attempt_no INTEGER NOT NULL, answers JSONB, score NUMERIC(5,2), passed BOOLEAN,
            started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, submitted_at TIMESTAMPTZ,
            CONSTRAINT uq_quiz_attempts_number UNIQUE (quiz_id, internship_member_id, attempt_no),
            CONSTRAINT ck_quiz_attempts_number CHECK (attempt_no > 0)
        )
        """,
        """
        CREATE TABLE tasks (
            id UUID PRIMARY KEY, internship_member_id UUID NOT NULL REFERENCES internship_members(id) ON DELETE CASCADE,
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title VARCHAR(255) NOT NULL, description TEXT, deadline TIMESTAMPTZ, priority VARCHAR(10),
            status VARCHAR(30) NOT NULL DEFAULT 'TODO', created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_tasks_priority CHECK (priority IS NULL OR priority IN ('LOW','MEDIUM','HIGH')),
            CONSTRAINT ck_tasks_status CHECK (status IN ('TODO','IN_PROGRESS','SUBMITTED','REVISION_REQUIRED','COMPLETED','CANCELLED'))
        )
        """,
        """
        CREATE TABLE task_submissions (
            id UUID PRIMARY KEY, task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            version INTEGER NOT NULL, content TEXT, file_url TEXT, status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
            review_comment TEXT, reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMPTZ,
            CONSTRAINT uq_task_submissions_version UNIQUE (task_id, version),
            CONSTRAINT ck_task_submissions_status CHECK (status IN ('SUBMITTED','REVISION_REQUIRED','ACCEPTED'))
        )
        """,
        """
        CREATE TABLE task_comments (
            id UUID PRIMARY KEY, task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE evaluation_criteria (
            id UUID PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE, description TEXT,
            max_score NUMERIC(5,2) NOT NULL, weight NUMERIC(5,2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_evaluation_criteria_max_score CHECK (max_score > 0),
            CONSTRAINT ck_evaluation_criteria_weight CHECK (weight >= 0 AND weight <= 100),
            CONSTRAINT ck_evaluation_criteria_status CHECK (status IN ('ACTIVE','INACTIVE'))
        )
        """,
        """
        CREATE TABLE evaluations (
            id UUID PRIMARY KEY, internship_member_id UUID NOT NULL REFERENCES internship_members(id) ON DELETE CASCADE,
            mentor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            evaluation_type VARCHAR(20) NOT NULL, criteria_scores JSONB NOT NULL, total_score NUMERIC(5,2),
            comment TEXT, status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_evaluations_type CHECK (evaluation_type IN ('PERIODIC','FINAL')),
            CONSTRAINT ck_evaluations_status CHECK (status IN ('DRAFT','PUBLISHED'))
        )
        """,
        """
        CREATE TABLE notifications (
            id UUID PRIMARY KEY, title VARCHAR(255) NOT NULL, content TEXT NOT NULL,
            target_type VARCHAR(20) NOT NULL, target_data JSONB,
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_notifications_target_type CHECK (target_type IN ('ALL','ROLE','USER'))
        )
        """,
        """
        CREATE TABLE notification_reads (
            notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            read_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (notification_id, user_id)
        )
        """,
        """
        CREATE TABLE ai_conversations (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255), created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE ai_messages (
            id UUID PRIMARY KEY, conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL, content TEXT NOT NULL, citations JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_ai_messages_role CHECK (role IN ('USER','ASSISTANT'))
        )
        """,
        "CREATE INDEX ix_internship_members_internship_id ON internship_members (internship_id)",
        "CREATE INDEX ix_internship_members_intern_id ON internship_members (intern_id)",
        "CREATE INDEX ix_internship_members_mentor_id ON internship_members (mentor_id)",
        "CREATE INDEX ix_internship_members_roadmap_id ON internship_members (roadmap_id)",
        "CREATE INDEX ix_internship_requests_internship_member_id ON internship_requests (internship_member_id)",
        "CREATE INDEX ix_internship_requests_status ON internship_requests (status)",
        "CREATE INDEX ix_phases_roadmap_id ON phases (roadmap_id)",
        "CREATE INDEX ix_learning_contents_phase_id ON learning_contents (phase_id)",
        "CREATE INDEX ix_learning_progress_internship_member_id ON learning_progress (internship_member_id)",
        "CREATE INDEX ix_learning_progress_content_id ON learning_progress (content_id)",
        "CREATE INDEX ix_quizzes_phase_id ON quizzes (phase_id)",
        "CREATE INDEX ix_questions_quiz_id ON questions (quiz_id)",
        "CREATE INDEX ix_quiz_attempts_quiz_id ON quiz_attempts (quiz_id)",
        "CREATE INDEX ix_quiz_attempts_internship_member_id ON quiz_attempts (internship_member_id)",
        "CREATE INDEX ix_tasks_internship_member_id ON tasks (internship_member_id)",
        "CREATE INDEX ix_tasks_created_by ON tasks (created_by)",
        "CREATE INDEX ix_tasks_deadline ON tasks (deadline)",
        "CREATE INDEX ix_tasks_status ON tasks (status)",
        "CREATE INDEX ix_tasks_member_deadline ON tasks (internship_member_id, deadline)",
        "CREATE INDEX ix_task_submissions_task_id ON task_submissions (task_id)",
        "CREATE INDEX ix_task_comments_task_id ON task_comments (task_id)",
        "CREATE INDEX ix_task_comments_user_id ON task_comments (user_id)",
        "CREATE INDEX ix_evaluations_member_id ON evaluations (internship_member_id)",
        "CREATE INDEX ix_evaluations_mentor_id ON evaluations (mentor_id)",
        "CREATE INDEX ix_notifications_created_by ON notifications (created_by)",
        "CREATE INDEX ix_notification_reads_user_id ON notification_reads (user_id)",
        "CREATE INDEX ix_ai_conversations_user_id ON ai_conversations (user_id)",
        "CREATE INDEX ix_ai_messages_conversation_id ON ai_messages (conversation_id)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    for table in (
        "ai_messages",
        "ai_conversations",
        "notification_reads",
        "notifications",
        "evaluations",
        "evaluation_criteria",
        "task_comments",
        "task_submissions",
        "tasks",
        "quiz_attempts",
        "questions",
        "quizzes",
        "learning_progress",
        "internship_requests",
        "internship_members",
        "learning_contents",
        "phases",
        "roadmaps",
        "internships",
        "users",
    ):
        op.execute(f"DROP TABLE {table}")
