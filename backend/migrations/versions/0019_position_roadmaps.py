"""Configure one roadmap per internship position without rewriting learning history.

Revision ID: 0019_position_roadmaps
Revises: 0018_file_documents_only

Existing roadmap positions intentionally remain NULL: names are not reliable
classification evidence. Administrators classify legacy curricula explicitly.
Membership roadmap assignments and all progress/attempt/history rows are preserved.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_position_roadmaps"
down_revision = "0018_file_documents_only"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lo_trinh_dao_tao", sa.Column("position", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_roadmaps_position",
        "lo_trinh_dao_tao",
        "position IS NULL OR position IN ('BACKEND','FRONTEND','FULLSTACK','AI','BA','OTHER')",
    )
    op.create_unique_constraint("uq_roadmaps_id_position", "lo_trinh_dao_tao", ["id", "position"])
    op.create_table(
        "internship_roadmaps",
        sa.Column(
            "internship_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dot_thuc_tap.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.String(20), primary_key=True),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("internship_id", "roadmap_id", name="uq_internship_roadmaps_roadmap"),
        sa.ForeignKeyConstraint(
            ["roadmap_id", "position"],
            ["lo_trinh_dao_tao.id", "lo_trinh_dao_tao.position"],
            name="fk_internship_roadmap_position",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.CheckConstraint(
            "position IN ('BACKEND','FRONTEND','FULLSTACK','AI','BA','OTHER')",
            name="ck_internship_roadmaps_position",
        ),
    )
    # No type inference or member reassignment. Only already typed valid defaults
    # can be represented; newly added nullable positions normally make this empty.
    op.execute(
        "INSERT INTO internship_roadmaps (internship_id, position, roadmap_id) "
        "SELECT d.id, r.position, r.id FROM dot_thuc_tap d "
        "JOIN lo_trinh_dao_tao r ON r.id = d.lo_trinh_id "
        "WHERE r.position IS NOT NULL AND r.status = 'ACTIVE'"
    )


def downgrade():
    op.drop_table("internship_roadmaps")
    op.drop_constraint("uq_roadmaps_id_position", "lo_trinh_dao_tao", type_="unique")
    op.drop_constraint("ck_roadmaps_position", "lo_trinh_dao_tao", type_="check")
    op.drop_column("lo_trinh_dao_tao", "position")
