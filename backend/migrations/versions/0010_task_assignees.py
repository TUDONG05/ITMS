"""Store shared task assignments as a many-to-many association.

Revision ID: 0010_task_assignees
Revises: 0009_internship_applications
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_task_assignees"
down_revision = "0009_internship_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phan_cong_cong_viec",
        sa.Column("cong_viec_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thanh_vien_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["cong_viec_id"], ["cong_viec.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thanh_vien_id"], ["thanh_vien_thuc_tap.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cong_viec_id", "thanh_vien_id"),
    )
    op.create_index("ix_task_assignees_member_id", "phan_cong_cong_viec", ["thanh_vien_id"])
    op.execute(
        "INSERT INTO phan_cong_cong_viec (cong_viec_id, thanh_vien_id) "
        "SELECT id, thanh_vien_id FROM cong_viec"
    )
    op.drop_index("ix_tasks_member_deadline", table_name="cong_viec")
    op.drop_index("ix_tasks_internship_member_id", table_name="cong_viec")
    op.drop_column("cong_viec", "thanh_vien_id")


def downgrade() -> None:
    # A scalar recipient cannot represent shared tasks; refuse to discard assignments.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM phan_cong_cong_viec GROUP BY cong_viec_id HAVING count(*) > 1)
            THEN RAISE EXCEPTION 'Cannot downgrade while shared tasks have multiple assignees';
            END IF;
        END $$
    """)
    op.add_column("cong_viec", sa.Column("thanh_vien_id", postgresql.UUID(as_uuid=True)))
    op.execute(
        "UPDATE cong_viec SET thanh_vien_id = a.thanh_vien_id "
        "FROM phan_cong_cong_viec a WHERE a.cong_viec_id = cong_viec.id"
    )
    op.alter_column("cong_viec", "thanh_vien_id", nullable=False)
    op.create_foreign_key(
        "cong_viec_thanh_vien_id_fkey",
        "cong_viec",
        "thanh_vien_thuc_tap",
        ["thanh_vien_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_tasks_internship_member_id", "cong_viec", ["thanh_vien_id"])
    op.create_index("ix_tasks_member_deadline", "cong_viec", ["thanh_vien_id", "deadline"])
    op.drop_table("phan_cong_cong_viec")
