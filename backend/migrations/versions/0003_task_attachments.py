"""Task attachments table for UC-7 (Mentor attaches documents to a Task).

Revision ID: 0003_task_attachments
Revises: 0002_vietnamese_schema_names
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_task_attachments"
down_revision: str | None = "0002_vietnamese_schema_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tep_dinh_kem_cong_viec (
            id UUID PRIMARY KEY,
            cong_viec_id UUID NOT NULL REFERENCES cong_viec(id) ON DELETE CASCADE,
            duong_dan_tep TEXT NOT NULL,
            ten_tep VARCHAR(255),
            dung_luong INTEGER,
            nguoi_tai_len_id UUID REFERENCES nguoi_dung(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_task_attachments_task_id"
        " ON tep_dinh_kem_cong_viec (cong_viec_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tep_dinh_kem_cong_viec")
