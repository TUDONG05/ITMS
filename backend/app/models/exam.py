from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Quiz(Base):
    __tablename__ = "bai_kiem_tra"
    __table_args__ = (
        CheckConstraint("thoi_luong_phut > 0", name="ck_quizzes_duration"),
        CheckConstraint("diem_dat >= 0 AND diem_dat <= 100", name="ck_quizzes_pass_score"),
        CheckConstraint("so_lan_lam_toi_da > 0", name="ck_quizzes_max_attempts"),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'CLOSED')", name="ck_quizzes_status"),
        Index("ix_quizzes_phase_id", "giai_doan_id"),
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
    duration_minutes: Mapped[int] = mapped_column("thoi_luong_phut", Integer, nullable=False)
    pass_score: Mapped[float] = mapped_column("diem_dat", Numeric(5, 2), nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        "so_lan_lam_toi_da", Integer, nullable=False, default=1
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Question(Base):
    __tablename__ = "cau_hoi"
    __table_args__ = (
        CheckConstraint(
            "loai IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'TRUE_FALSE', 'TEXT')",
            name="ck_questions_type",
        ),
        Index("ix_questions_quiz_id", "bai_kiem_tra_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        "bai_kiem_tra_id",
        UUID(as_uuid=True),
        ForeignKey("bai_kiem_tra.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column("noi_dung", Text, nullable=False)
    type: Mapped[str] = mapped_column("loai", String(30), nullable=False)
    options: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        "lua_chon", JSONB, nullable=True
    )
    correct_answer: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        "dap_an_dung", JSONB, nullable=False
    )
    score: Mapped[float] = mapped_column("diem", Numeric(5, 2), nullable=False)
    order_no: Mapped[int | None] = mapped_column("thu_tu", Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class QuizAttempt(Base):
    __tablename__ = "lan_lam_bai"
    __table_args__ = (
        UniqueConstraint(
            "bai_kiem_tra_id", "thanh_vien_id", "lan_lam", name="uq_quiz_attempts_number"
        ),
        CheckConstraint("lan_lam > 0", name="ck_quiz_attempts_number"),
        Index("ix_quiz_attempts_quiz_id", "bai_kiem_tra_id"),
        Index("ix_quiz_attempts_internship_member_id", "thanh_vien_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        "bai_kiem_tra_id",
        UUID(as_uuid=True),
        ForeignKey("bai_kiem_tra.id", ondelete="CASCADE"),
        nullable=False,
    )
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column("lan_lam", Integer, nullable=False)
    answers: Mapped[list[Any] | None] = mapped_column("cau_tra_loi", JSONB, nullable=True)
    score: Mapped[float | None] = mapped_column("diem", Numeric(5, 2), nullable=True)
    passed: Mapped[bool | None] = mapped_column("dat", Boolean, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
