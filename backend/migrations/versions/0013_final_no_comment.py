"""Remove obsolete comments from final evaluations.

Revision ID: 0013_final_no_comment
Revises: 0012_evaluation_weekly_final

Weekly and periodic evaluations continue to use nhan_xet. Final evaluations
use ket_luan and ly_do_ket_luan instead.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_final_no_comment"
down_revision: str | None = "0012_evaluation_weekly_final"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE danh_gia SET nhan_xet = NULL WHERE loai_danh_gia = 'FINAL'")


def downgrade() -> None:
    # Removed comments cannot be reconstructed. No schema change to undo.
    pass
