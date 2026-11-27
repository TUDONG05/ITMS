"""Store the internship position selected by applicants.

Revision ID: 0016_application_position
Revises: 0015_member_position
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_application_position"
down_revision: str | None = "0015_member_position"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("don_dang_ky_thuc_tap", sa.Column("position", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_internship_applications_position",
        "don_dang_ky_thuc_tap",
        "position IS NULL OR position IN ('BACKEND','FRONTEND','FULLSTACK','AI','BA','OTHER')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_internship_applications_position", "don_dang_ky_thuc_tap", type_="check")
    op.drop_column("don_dang_ky_thuc_tap", "position")
