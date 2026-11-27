"""Allow each intern to belong to one internship for their lifetime.

Revision ID: 0014_single_internship
Revises: 0013_final_no_comment
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_single_internship"
down_revision: str | None = "0013_final_no_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_count = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM (SELECT thuc_tap_sinh_id FROM thanh_vien_thuc_tap "
                "GROUP BY thuc_tap_sinh_id HAVING count(*) > 1) AS duplicates"
            )
        )
        .scalar_one()
    )
    if duplicate_count:
        raise RuntimeError(
            f"Cannot enforce one internship per intern: {duplicate_count} interns have multiple "
            "memberships. Back up the database, choose the membership to retain for each intern, "
            "and reconcile dependent records before retrying. This migration never deletes data."
        )
    op.create_unique_constraint(
        "uq_internship_members_single_intern", "thanh_vien_thuc_tap", ["thuc_tap_sinh_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_internship_members_single_intern", "thanh_vien_thuc_tap", type_="unique")
