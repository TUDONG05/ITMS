from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    __tablename__ = "cong_viec"
    __table_args__ = (
        CheckConstraint("uu_tien IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_tasks_priority"),
        CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'SUBMITTED', "
            "'REVISION_REQUIRED', 'COMPLETED', 'CANCELLED')",
            name="ck_tasks_status",
        ),
        Index("ix_tasks_internship_member_id", "thanh_vien_id"),
        Index("ix_tasks_created_by", "nguoi_tao_id"),
        Index("ix_tasks_deadline", "deadline"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_member_deadline", "thanh_vien_id", "deadline"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        "nguoi_tao_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column("tieu_de", String(255), nullable=False)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str | None] = mapped_column("uu_tien", String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="TODO")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class TaskSubmission(Base):
    __tablename__ = "bai_nop_cong_viec"
    __table_args__ = (
        UniqueConstraint("cong_viec_id", "version", name="uq_task_submissions_version"),
        CheckConstraint(
            "status IN ('SUBMITTED', 'REVISION_REQUIRED', 'ACCEPTED')",
            name="ck_task_submissions_status",
        ),
        Index("ix_task_submissions_task_id", "cong_viec_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        "cong_viec_id",
        UUID(as_uuid=True),
        ForeignKey("cong_viec.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str | None] = mapped_column("noi_dung", Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUBMITTED")
    review_comment: Mapped[str | None] = mapped_column("nhan_xet", Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        "nguoi_duyet_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskComment(Base):
    __tablename__ = "binh_luan_cong_viec"
    __table_args__ = (
        Index("ix_task_comments_task_id", "cong_viec_id"),
        Index("ix_task_comments_user_id", "nguoi_dung_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        "cong_viec_id",
        UUID(as_uuid=True),
        ForeignKey("cong_viec.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "nguoi_dung_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column("noi_dung", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
