"""Merge the final-verdict reason into the evaluation comment.

Revision ID: 0013_evaluation_final_comment
Revises: 0012_evaluation_weekly_final
Create Date: 2026-11-08

Đánh giá cuối cùng chỉ còn một ô "Nhận xét" (nêu lý do của kết luận Đạt/Chưa đạt). Lý do đã
nhập trước đó được ghép vào đầu nhận xét rồi cột ly_do_ket_luan bị bỏ.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_evaluation_final_comment"
down_revision: str | None = "0012_evaluation_weekly_final"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE danh_gia
        SET nhan_xet = CASE
            WHEN nhan_xet IS NULL OR btrim(nhan_xet) = '' THEN btrim(ly_do_ket_luan)
            ELSE btrim(ly_do_ket_luan) || E'\\n\\n' || nhan_xet
        END
        WHERE ly_do_ket_luan IS NOT NULL AND btrim(ly_do_ket_luan) <> ''
        """
    )
    op.drop_column("danh_gia", "ly_do_ket_luan")


def downgrade() -> None:
    # Lý do đã nằm trong nhận xét nên không tách lại được; chỉ khôi phục cột (rỗng).
    op.add_column("danh_gia", sa.Column("ly_do_ket_luan", sa.Text(), nullable=True))
