"""Create persistent authentication sessions.

Revision ID: 0007_auth_sessions
Revises: 0006_merge_task_todo_status
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_auth_sessions"
down_revision: str | None = "0006_merge_task_todo_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "phien_dang_nhap",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["nguoi_dung.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_phien_dang_nhap_refresh_token_hash",
        "phien_dang_nhap",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index("ix_phien_dang_nhap_user_id", "phien_dang_nhap", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_phien_dang_nhap_user_id", table_name="phien_dang_nhap")
    op.drop_index("ix_phien_dang_nhap_refresh_token_hash", table_name="phien_dang_nhap")
    op.drop_table("phien_dang_nhap")
