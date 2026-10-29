"""Create table for internship applications.

Revision ID: 0009_internship_applications
Revises: 0008_internship_roadmap
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_internship_applications"
down_revision: str | None = "0008_internship_roadmap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "don_dang_ky_thuc_tap",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dot_thuc_tap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thuc_tap_sinh_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trang_thai", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("ly_do", sa.Text(), nullable=True),
        sa.Column("nguoi_duyet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ghi_chu_duyet", sa.Text(), nullable=True),
        sa.Column(
            "ngay_tao",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ngay_duyet", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dot_thuc_tap_id"],
            ["dot_thuc_tap.id"],
            name="fk_don_dang_ky_dot_thuc_tap_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["thuc_tap_sinh_id"],
            ["nguoi_dung.id"],
            name="fk_don_dang_ky_thuc_tap_sinh_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["nguoi_duyet_id"],
            ["nguoi_dung.id"],
            name="fk_don_dang_ky_nguoi_duyet_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dot_thuc_tap_id",
            "thuc_tap_sinh_id",
            name="uq_don_dang_ky_dot_intern",
        ),
        sa.CheckConstraint(
            "trang_thai IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="ck_don_dang_ky_trang_thai",
        ),
    )
    op.create_index(
        "ix_don_dang_ky_trang_thai",
        "don_dang_ky_thuc_tap",
        ["trang_thai"],
        unique=False,
    )
    op.create_index(
        "ix_don_dang_ky_thuc_tap_sinh_id",
        "don_dang_ky_thuc_tap",
        ["thuc_tap_sinh_id"],
        unique=False,
    )
    op.create_index(
        "ix_don_dang_ky_dot_thuc_tap_id",
        "don_dang_ky_thuc_tap",
        ["dot_thuc_tap_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_don_dang_ky_dot_thuc_tap_id", table_name="don_dang_ky_thuc_tap")
    op.drop_index("ix_don_dang_ky_thuc_tap_sinh_id", table_name="don_dang_ky_thuc_tap")
    op.drop_index("ix_don_dang_ky_trang_thai", table_name="don_dang_ky_thuc_tap")
    op.drop_table("don_dang_ky_thuc_tap")
