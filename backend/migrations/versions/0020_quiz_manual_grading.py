"""Add manual grading status and per-question grades to quiz attempts.

Revision ID: 0020_quiz_manual_grading
Revises: 0019_position_roadmaps
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020_quiz_manual_grading"
down_revision = "0019_position_roadmaps"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "lan_lam_bai",
        sa.Column(
            "trang_thai_cham",
            sa.String(20),
            nullable=False,
            server_default="AUTO_GRADED",
        ),
    )
    op.create_check_constraint(
        "ck_quiz_attempts_grading_status",
        "lan_lam_bai",
        "trang_thai_cham IN ('AUTO_GRADED', 'PENDING_GRADING', 'GRADED')",
    )
    op.add_column(
        "lan_lam_bai",
        sa.Column("diem_chi_tiet", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("lan_lam_bai", "diem_chi_tiet")
    op.drop_constraint("ck_quiz_attempts_grading_status", "lan_lam_bai", type_="check")
    op.drop_column("lan_lam_bai", "trang_thai_cham")
