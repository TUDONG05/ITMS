"""Support group work or individual submissions on one shared task.

Revision ID: 0011_task_assignment_modes
Revises: 0010_task_assignees
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_task_assignment_modes"
down_revision = "0010_task_assignees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cong_viec",
        sa.Column("assignment_mode", sa.String(20), nullable=False, server_default="GROUP"),
    )
    op.create_check_constraint(
        "ck_tasks_assignment_mode", "cong_viec", "assignment_mode IN ('GROUP', 'INDIVIDUAL')"
    )
    op.add_column(
        "phan_cong_cong_viec",
        sa.Column("status", sa.String(30), nullable=False, server_default="TODO"),
    )
    op.execute(
        "UPDATE phan_cong_cong_viec a SET status=t.status "
        "FROM cong_viec t WHERE t.id=a.cong_viec_id"
    )
    op.create_check_constraint(
        "ck_task_assignees_status",
        "phan_cong_cong_viec",
        "status IN ('TODO','SUBMITTED','REVISION_REQUIRED','COMPLETED','CANCELLED')",
    )
    op.add_column("bai_nop_cong_viec", sa.Column("thanh_vien_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_task_submission_member",
        "bai_nop_cong_viec",
        "thanh_vien_thuc_tap",
        ["thanh_vien_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_task_submission_task", "bai_nop_cong_viec", type_="unique")
    op.create_index(
        "uq_task_submission_group",
        "bai_nop_cong_viec",
        ["cong_viec_id"],
        unique=True,
        postgresql_where=sa.text("thanh_vien_id IS NULL"),
    )
    op.create_index(
        "uq_task_submission_individual",
        "bai_nop_cong_viec",
        ["cong_viec_id", "thanh_vien_id"],
        unique=True,
        postgresql_where=sa.text("thanh_vien_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM cong_viec WHERE assignment_mode='INDIVIDUAL') THEN
            RAISE EXCEPTION 'Cannot downgrade while individual tasks exist';
        END IF;
    END $$""")
    op.drop_index("uq_task_submission_individual", table_name="bai_nop_cong_viec")
    op.drop_index("uq_task_submission_group", table_name="bai_nop_cong_viec")
    op.create_unique_constraint("uq_task_submission_task", "bai_nop_cong_viec", ["cong_viec_id"])
    op.drop_column("bai_nop_cong_viec", "thanh_vien_id")
    op.drop_column("phan_cong_cong_viec", "status")
    op.drop_column("cong_viec", "assignment_mode")
