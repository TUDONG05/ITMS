"""Add weekly comments and final verdict to evaluations.

Revision ID: 0012_evaluation_weekly_final
Revises: 0011_task_assignment_modes
Create Date: 2026-11-05

Nhận xét tuần (WEEKLY) có khoảng thời gian bắt đầu/kết thúc. Đánh giá cuối cùng (FINAL) có
kết luận Đạt/Chưa đạt (ket_luan) và lý do (ly_do_ket_luan).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_evaluation_weekly_final"
down_revision: str | None = "0011_task_assignment_modes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("danh_gia", sa.Column("tuan_bat_dau", sa.Date(), nullable=True))
    op.add_column("danh_gia", sa.Column("tuan_ket_thuc", sa.Date(), nullable=True))
    op.add_column("danh_gia", sa.Column("ket_luan", sa.String(length=10), nullable=True))
    op.add_column("danh_gia", sa.Column("ly_do_ket_luan", sa.Text(), nullable=True))
    op.execute("ALTER TABLE danh_gia DROP CONSTRAINT IF EXISTS ck_evaluations_type")
    op.execute(
        "ALTER TABLE danh_gia ADD CONSTRAINT ck_evaluations_type "
        "CHECK (loai_danh_gia IN ('WEEKLY','PERIODIC','FINAL'))"
    )
    op.execute(
        "ALTER TABLE danh_gia ADD CONSTRAINT ck_evaluations_verdict "
        "CHECK (ket_luan IS NULL OR ket_luan IN ('PASS','FAIL'))"
    )
    op.execute(
        "ALTER TABLE danh_gia ADD CONSTRAINT ck_evaluations_verdict_final "
        "CHECK (ket_luan IS NULL OR loai_danh_gia = 'FINAL')"
    )
    op.execute(
        "ALTER TABLE danh_gia ADD CONSTRAINT ck_evaluations_week_range CHECK ("
        "(loai_danh_gia = 'WEEKLY' AND tuan_bat_dau IS NOT NULL AND tuan_ket_thuc IS NOT NULL "
        "AND tuan_ket_thuc >= tuan_bat_dau) OR "
        "(loai_danh_gia <> 'WEEKLY' AND tuan_bat_dau IS NULL AND tuan_ket_thuc IS NULL))"
    )
    op.create_index(
        "uq_evaluations_final_per_member",
        "danh_gia",
        ["thanh_vien_id"],
        unique=True,
        postgresql_where=sa.text("loai_danh_gia = 'FINAL'"),
    )


def downgrade() -> None:
    # Hạ cấp xóa các nhận xét tuần vì phiên bản cũ không có loại WEEKLY.
    op.execute("DELETE FROM danh_gia WHERE loai_danh_gia = 'WEEKLY'")
    op.drop_index("uq_evaluations_final_per_member", table_name="danh_gia")
    op.execute("ALTER TABLE danh_gia DROP CONSTRAINT IF EXISTS ck_evaluations_week_range")
    op.execute("ALTER TABLE danh_gia DROP CONSTRAINT IF EXISTS ck_evaluations_verdict_final")
    op.execute("ALTER TABLE danh_gia DROP CONSTRAINT IF EXISTS ck_evaluations_verdict")
    op.execute("ALTER TABLE danh_gia DROP CONSTRAINT IF EXISTS ck_evaluations_type")
    op.execute(
        "ALTER TABLE danh_gia ADD CONSTRAINT ck_evaluations_type "
        "CHECK (loai_danh_gia IN ('PERIODIC','FINAL'))"
    )
    op.drop_column("danh_gia", "ly_do_ket_luan")
    op.drop_column("danh_gia", "ket_luan")
    op.drop_column("danh_gia", "tuan_ket_thuc")
    op.drop_column("danh_gia", "tuan_bat_dau")
