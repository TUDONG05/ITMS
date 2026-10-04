"""Single submission per task for UC-7 (resubmit overwrites, no versions).

Revision ID: 0005_single_task_submission
Revises: 0004_task_attachment_column
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_single_task_submission"
down_revision: str | None = "0004_task_attachment_column"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE bai_nop_cong_viec DROP CONSTRAINT IF EXISTS uq_task_submissions_version"
    )
    op.execute("ALTER TABLE bai_nop_cong_viec DROP COLUMN IF EXISTS version")
    # Gộp dữ liệu cũ: mỗi task chỉ giữ lại bài nộp mới nhất
    op.execute(
        """
        DELETE FROM bai_nop_cong_viec a
        WHERE EXISTS (
            SELECT 1 FROM bai_nop_cong_viec b
            WHERE b.cong_viec_id = a.cong_viec_id
              AND (b.submitted_at, b.id) > (a.submitted_at, a.id)
        )
        """
    )
    op.execute(
        "ALTER TABLE bai_nop_cong_viec ADD CONSTRAINT uq_task_submission_task UNIQUE (cong_viec_id)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE bai_nop_cong_viec DROP CONSTRAINT IF EXISTS uq_task_submission_task")
    op.execute("ALTER TABLE bai_nop_cong_viec ADD COLUMN IF NOT EXISTS version INTEGER")
    op.execute(
        "ALTER TABLE bai_nop_cong_viec"
        " ADD CONSTRAINT uq_task_submissions_version UNIQUE (cong_viec_id, version)"
    )
