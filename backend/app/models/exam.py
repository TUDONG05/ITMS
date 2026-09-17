from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExamAttemptStatus, QuestionDifficulty, QuestionType

if TYPE_CHECKING:
    from app.models.roadmap import RoadmapPhase
    from app.models.user import User


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_exams_duration"),
        CheckConstraint("max_attempts > 0", name="ck_exams_attempts"),
        CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100", name="ck_exams_passing_score"
        ),
        CheckConstraint("close_at > open_at", name="ck_exams_dates"),
        Index("ix_exams_phase_id", "phase_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roadmap_phases.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    passing_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    phase: Mapped[RoadmapPhase] = relationship("RoadmapPhase", back_populates="exams")
    exam_questions: Mapped[list[ExamQuestion]] = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.order_no",
    )
    attempts: Mapped[list[ExamAttempt]] = relationship(
        "ExamAttempt", back_populates="exam", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", native_enum=True), nullable=False
    )
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="question_difficulty", native_enum=True),
        nullable=False,
        default=QuestionDifficulty.MEDIUM,
    )
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    exam_questions: Mapped[list[ExamQuestion]] = relationship(
        "ExamQuestion", back_populates="question", cascade="all, delete-orphan"
    )
    attempt_answers: Mapped[list[AttemptAnswer]] = relationship(
        "AttemptAnswer", back_populates="question", cascade="all, delete-orphan"
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_questions_exam_question"),
        UniqueConstraint("exam_id", "order_no", name="uq_exam_questions_order"),
        Index("ix_exam_questions_exam_id", "exam_id"),
        Index("ix_exam_questions_question_id", "question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)

    # Relationships
    exam: Mapped[Exam] = relationship("Exam", back_populates="exam_questions")
    question: Mapped[Question] = relationship("Question", back_populates="exam_questions")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    __table_args__ = (
        UniqueConstraint("exam_id", "intern_id", "attempt_no", name="uq_exam_attempts_no"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="ck_exam_attempts_score"
        ),
        Index("ix_exam_attempts_exam_id", "exam_id"),
        Index("ix_exam_attempts_intern_id", "intern_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    intern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ExamAttemptStatus] = mapped_column(
        Enum(ExamAttemptStatus, name="exam_attempt_status", native_enum=True),
        nullable=False,
        default=ExamAttemptStatus.IN_PROGRESS,
    )

    # Relationships
    exam: Mapped[Exam] = relationship("Exam", back_populates="attempts")
    intern: Mapped[User] = relationship("User", back_populates="exam_attempts")
    answers: Mapped[list[AttemptAnswer]] = relationship(
        "AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_question"),
        Index("ix_attempt_answers_attempt_id", "attempt_id"),
        Index("ix_attempt_answers_question_id", "question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    attempt: Mapped[ExamAttempt] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped[Question] = relationship("Question", back_populates="attempt_answers")
