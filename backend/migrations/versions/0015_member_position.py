"""Store the assigned internship position on each membership.

Revision ID: 0015_member_position
Revises: 0014_single_internship
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_member_position"
down_revision: str | None = "0014_single_internship"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("thanh_vien_thuc_tap", sa.Column("position", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_internship_members_position",
        "thanh_vien_thuc_tap",
        "position IS NULL OR position IN ('BACKEND','FRONTEND','FULLSTACK','AI','BA','OTHER')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_internship_members_position", "thanh_vien_thuc_tap", type_="check")
    op.drop_column("thanh_vien_thuc_tap", "position")
