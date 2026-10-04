"""Replace task attachments table with a single url_tep column on cong_viec.

Revision ID: 0004_task_attachment_column
Revises: 0003_task_attachments
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_task_attachment_column"
down_revision: str | None = "0003_task_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tep_dinh_kem_cong_viec")
    op.execute("ALTER TABLE cong_viec ADD COLUMN IF NOT EXISTS url_tep TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE cong_viec DROP COLUMN IF EXISTS url_tep")
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
