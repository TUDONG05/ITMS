"""Assign a training roadmap to an internship batch.

Revision ID: 0008_internship_roadmap
Revises: 0007_auth_sessions
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_internship_roadmap"
down_revision: str | None = "0007_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dot_thuc_tap",
        sa.Column("lo_trinh_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dot_thuc_tap_lo_trinh_id",
        "dot_thuc_tap",
        "lo_trinh_dao_tao",
        ["lo_trinh_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_internships_roadmap_id",
        "dot_thuc_tap",
        ["lo_trinh_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_internships_roadmap_id", table_name="dot_thuc_tap")
    op.drop_constraint("fk_dot_thuc_tap_lo_trinh_id", "dot_thuc_tap", type_="foreignkey")
    op.drop_column("dot_thuc_tap", "lo_trinh_id")
