from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Roadmap(Base):
    __tablename__ = "lo_trinh_dao_tao"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')", name="ck_roadmaps_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("ten", String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        "nguoi_tao_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Phase(Base):
    __tablename__ = "giai_doan"
    __table_args__ = (
        UniqueConstraint("lo_trinh_id", "thu_tu", name="uq_phases_roadmap_order"),
        Index("ix_phases_roadmap_id", "lo_trinh_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        "lo_trinh_id",
        UUID(as_uuid=True),
        ForeignKey("lo_trinh_dao_tao.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column("ten", String(200), nullable=False)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    order_no: Mapped[int] = mapped_column("thu_tu", Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class LearningContent(Base):
    __tablename__ = "noi_dung_dao_tao"
    __table_args__ = (
        UniqueConstraint("giai_doan_id", "thu_tu", name="uq_learning_contents_phase_order"),
        CheckConstraint(
            "loai IN ('LESSON', 'DOCUMENT', 'VIDEO', 'LINK')", name="ck_learning_contents_type"
        ),
        Index("ix_learning_contents_phase_id", "giai_doan_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        "giai_doan_id",
        UUID(as_uuid=True),
        ForeignKey("giai_doan.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column("tieu_de", String(255), nullable=False)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    type: Mapped[str] = mapped_column("loai", String(20), nullable=False)
    content: Mapped[str | None] = mapped_column("noi_dung", Text, nullable=True)
    resource_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_no: Mapped[int] = mapped_column("thu_tu", Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class LearningProgress(Base):
    __tablename__ = "tien_do_hoc_tap"
    __table_args__ = (
        UniqueConstraint(
            "thanh_vien_id", "noi_dung_id", name="uq_learning_progress_member_content"
        ),
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_learning_progress_status",
        ),
        CheckConstraint(
            "phan_tram_tien_do >= 0 AND phan_tram_tien_do <= 100",
            name="ck_learning_progress_percent",
        ),
        Index("ix_learning_progress_internship_member_id", "thanh_vien_id"),
        Index("ix_learning_progress_content_id", "noi_dung_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        "noi_dung_id",
        UUID(as_uuid=True),
        ForeignKey("noi_dung_dao_tao.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    progress_percent: Mapped[float] = mapped_column(
        "phan_tram_tien_do", Numeric(5, 2), nullable=False, default=0
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
