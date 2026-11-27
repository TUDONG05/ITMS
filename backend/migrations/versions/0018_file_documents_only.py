"""Restrict the shared catalog to supported file documents.

Revision ID: 0018_file_documents_only
Revises: 0017_document_library

Legacy webpage URLs remain exactly as stored on learning contents. Only their
catalog entries and catalog associations are removed.
"""

import sqlalchemy as sa
from alembic import op

revision = "0018_file_documents_only"
down_revision = "0017_document_library"
branch_labels = None
depends_on = None

FILE_FORMATS = (
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "md",
    "csv",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "mp4",
    "webm",
    "mp3",
    "wav",
    "zip",
)
FORMAT_CHECK = "format IN (" + ",".join(repr(value) for value in FILE_FORMATS) + ")"


def upgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM learning_content_documents WHERE document_id IN "
            "(SELECT id FROM document_library WHERE NOT (" + FORMAT_CHECK + "))"
        )
    )
    connection.execute(sa.text("DELETE FROM document_library WHERE NOT (" + FORMAT_CHECK + ")"))
    op.create_check_constraint("ck_documents_file_format", "document_library", FORMAT_CHECK)


def downgrade():
    # Removed catalog metadata is recoverable from backups; legacy lesson URLs were never changed.
    op.drop_constraint("ck_documents_file_format", "document_library", type_="check")
