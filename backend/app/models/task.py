from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    case,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "cong_viec"
    __table_args__ = (
        CheckConstraint("uu_tien IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_tasks_priority"),
        CheckConstraint(
            "assignment_mode IN ('GROUP', 'INDIVIDUAL')", name="ck_tasks_assignment_mode"
        ),
        CheckConstraint(
            "status IN ('TODO', 'SUBMITTED', 'REVISION_REQUIRED', 'COMPLETED', 'CANCELLED')",
            name="ck_tasks_status",
        ),
        Index("ix_tasks_created_by", "nguoi_tao_id"),
        Index("ix_tasks_deadline", "deadline"),
        Index("ix_tasks_status", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignees: Mapped[list[TaskAssignee]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        "nguoi_tao_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column("tieu_de", String(255), nullable=False)
    assignment_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="GROUP")
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str | None] = mapped_column("uu_tien", String(10), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column("url_tep", Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="TODO")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class TaskAssignee(Base):
    __tablename__ = "phan_cong_cong_viec"
    __table_args__ = (
        Index("ix_task_assignees_member_id", "thanh_vien_id"),
        CheckConstraint(
            "status IN ('TODO', 'SUBMITTED', 'REVISION_REQUIRED', 'COMPLETED', 'CANCELLED')",
            name="ck_task_assignees_status",
        ),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        "cong_viec_id",
        UUID(as_uuid=True),
        ForeignKey("cong_viec.id", ondelete="CASCADE"),
        primary_key=True,
    )
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        primary_key=True,
    )
    task: Mapped[Task] = relationship(back_populates="assignees")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="TODO")


class TaskSubmission(Base):
    __tablename__ = "bai_nop_cong_viec"
    __table_args__ = (
        Index(
            "uq_task_submission_group",
            "cong_viec_id",
            unique=True,
            postgresql_where=text("thanh_vien_id IS NULL"),
        ),
        Index(
            "uq_task_submission_individual",
            "cong_viec_id",
            "thanh_vien_id",
            unique=True,
            postgresql_where=text("thanh_vien_id IS NOT NULL"),
        ),
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
    content: Mapped[str | None] = mapped_column("noi_dung", Text, nullable=True)
    internship_member_id: Mapped[uuid.UUID | None] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=True,
    )
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


def task_status_for_members(member_ids):
    """An intern sees their own result for individual work, or the shared group state."""
    own_status = (
        select(TaskAssignee.status)
        .where(TaskAssignee.task_id == Task.id, TaskAssignee.internship_member_id.in_(member_ids))
        .correlate(Task)
        .limit(1)
        .scalar_subquery()
    )
    return case((Task.assignment_mode == "INDIVIDUAL", own_status), else_=Task.status)
