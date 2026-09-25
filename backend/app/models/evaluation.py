from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvaluationCriterion(Base):
    __tablename__ = "tieu_chi_danh_gia"
    __table_args__ = (
        CheckConstraint("diem_toi_da > 0", name="ck_evaluation_criteria_max_score"),
        CheckConstraint("trong_so >= 0 AND trong_so <= 100", name="ck_evaluation_criteria_weight"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_evaluation_criteria_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("ten", String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    max_score: Mapped[float] = mapped_column("diem_toi_da", Numeric(5, 2), nullable=False)
    weight: Mapped[float] = mapped_column("trong_so", Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Evaluation(Base):
    __tablename__ = "danh_gia"
    __table_args__ = (
        CheckConstraint("loai_danh_gia IN ('PERIODIC', 'FINAL')", name="ck_evaluations_type"),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED')", name="ck_evaluations_status"),
        Index("ix_evaluations_member_id", "thanh_vien_id"),
        Index("ix_evaluations_mentor_id", "nguoi_huong_dan_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        "nguoi_huong_dan_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evaluation_type: Mapped[str] = mapped_column("loai_danh_gia", String(20), nullable=False)
    criteria_scores: Mapped[list[Any]] = mapped_column("diem_tieu_chi", JSONB, nullable=False)
    total_score: Mapped[float | None] = mapped_column("tong_diem", Numeric(5, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column("nhan_xet", Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
