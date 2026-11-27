"""Create a reusable document catalog and index existing training resources.

Revision ID: 0017_document_library
Revises: 0016_application_position
"""

import json
import re
import uuid
from datetime import UTC, datetime
from urllib.parse import unquote, urlsplit

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017_document_library"
down_revision = "0016_application_position"
branch_labels = None
depends_on = None


def legacy_urls(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        parsed = value
    values = parsed if isinstance(parsed, list) else [parsed]
    return list(
        dict.fromkeys(
            value.strip()
            for value in values
            if isinstance(value, str)
            and value.strip()
            and (
                urlsplit(value.strip()).scheme in ("http", "https")
                or value.strip().startswith("/api/v1/uploads/training/")
            )
        )
    )


def upgrade():
    op.create_table(
        "document_library",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("positions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("format = lower(format)", name="ck_documents_format_lower"),
        sa.CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_documents_size"),
        sa.CheckConstraint(
            'jsonb_typeof(positions) = \'array\' AND positions <@ \'["BACKEND","FRONTEND","FULLSTACK","AI","BA","OTHER"]\'::jsonb',
            name="ck_documents_positions",
        ),
    )
    op.create_index(
        "ix_documents_positions", "document_library", ["positions"], postgresql_using="gin"
    )
    op.create_index("ix_documents_format", "document_library", ["format"])
    op.create_table(
        "learning_content_documents",
        sa.Column(
            "content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("noi_dung_dao_tao.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_library.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_content_documents_document_id", "learning_content_documents", ["document_id"]
    )
    conn = op.get_bind()
    catalog = sa.table(
        "document_library",
        sa.column("id", postgresql.UUID()),
        sa.column("title"),
        sa.column("description"),
        sa.column("url"),
        sa.column("format"),
        sa.column("positions", postgresql.JSONB()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    links = sa.table(
        "learning_content_documents",
        sa.column("content_id", postgresql.UUID()),
        sa.column("document_id", postgresql.UUID()),
    )
    known = {}
    rows = conn.execute(
        sa.text("SELECT id, tieu_de, resource_url FROM noi_dung_dao_tao ORDER BY created_at, id")
    ).mappings()
    for row in rows:
        for url in legacy_urls(row["resource_url"]):
            document_id = known.get(url)
            if document_id is None:
                document_id = uuid.uuid4()
                known[url] = document_id
                path = unquote(urlsplit(url).path)
                extension = re.search(r"\.([A-Za-z0-9]{1,15})$", path)
                title = (row["tieu_de"] or path.rsplit("/", 1)[-1] or "Tài liệu")[:255]
                conn.execute(
                    catalog.insert().values(
                        id=document_id,
                        title=title,
                        description=None,
                        url=url,
                        format=extension.group(1).lower() if extension else "link",
                        positions=[],
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )
            conn.execute(links.insert().values(content_id=row["id"], document_id=document_id))


def downgrade():
    # Materialized resource URLs remain on learning content for backward compatibility.
    op.drop_table("learning_content_documents")
    op.drop_table("document_library")
