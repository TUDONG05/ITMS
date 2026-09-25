from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.internship import InternshipMember
    from app.models.roadmap import Phase


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        Index("ix_quizzes_phase_id", "phase_id"),
        Index("ix_quizzes_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("phases.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    phase: Mapped[Phase] = relationship("Phase", back_populates="quizzes")
    questions: Mapped[list[Question]] = relationship(
        "Question",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="Question.order_no",
    )
    attempts: Mapped[list[QuizAttempt]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_quiz_id", "quiz_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="SINGLE_CHOICE")
    options: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    correct_answer: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(
        JSONB, nullable=True
    )
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint(
            "quiz_id", "internship_member_id", "attempt_no", name="uq_quiz_attempts_no"
        ),
        Index("ix_quiz_attempts_quiz_id", "quiz_id"),
        Index("ix_quiz_attempts_member_id", "internship_member_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    answers: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="attempts")
    member: Mapped[InternshipMember] = relationship(
        "InternshipMember", back_populates="quiz_attempts"
    )
