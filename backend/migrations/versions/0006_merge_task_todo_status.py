"""Merge task IN_PROGRESS into TODO.

Revision ID: 0006_merge_task_todo_status
Revises: 0005_single_task_submission
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_merge_task_todo_status"
down_revision: str | None = "0005_single_task_submission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE cong_viec SET status = 'TODO' WHERE status = 'IN_PROGRESS'")
    op.execute("ALTER TABLE cong_viec DROP CONSTRAINT IF EXISTS ck_tasks_status")
    op.execute(
        "ALTER TABLE cong_viec ADD CONSTRAINT ck_tasks_status "
        "CHECK (status IN ('TODO','SUBMITTED','REVISION_REQUIRED','COMPLETED','CANCELLED'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cong_viec DROP CONSTRAINT IF EXISTS ck_tasks_status")
    op.execute(
        "ALTER TABLE cong_viec ADD CONSTRAINT ck_tasks_status "
        "CHECK (status IN ('TODO','IN_PROGRESS','SUBMITTED','REVISION_REQUIRED',"
        "'COMPLETED','CANCELLED'))"
    )
