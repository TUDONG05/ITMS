from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import InternshipPeriodStatus, InternshipStatus

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation, LifecycleRequest
    from app.models.roadmap import Roadmap
    from app.models.task import Task
    from app.models.user import User


class InternshipPeriod(Base):
    __tablename__ = "internship_periods"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_internship_periods_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InternshipPeriodStatus] = mapped_column(
        Enum(InternshipPeriodStatus, name="internship_period_status", native_enum=True),
        nullable=False,
        default=InternshipPeriodStatus.PLANNED,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    internships: Mapped[list[Internship]] = relationship(
        "Internship", back_populates="period", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list[Roadmap]] = relationship(
        "Roadmap", back_populates="period", cascade="all, delete-orphan"
    )


class Internship(Base):
    __tablename__ = "internships"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_internships_dates"),
        Index("ix_internships_period_id", "period_id"),
        Index("ix_internships_intern_id", "intern_id"),
        Index("ix_internships_status", "status"),
        Index(
            "uq_internships_active_intern",
            "intern_id",
            unique=True,
            postgresql_where=(mapped_column("status") == "ACTIVE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internship_periods.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[InternshipStatus] = mapped_column(
        Enum(InternshipStatus, name="internship_status", native_enum=True),
        nullable=False,
        default=InternshipStatus.PLANNED,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    intern: Mapped[User] = relationship(
        "User", back_populates="internships", foreign_keys=[intern_id]
    )
    period: Mapped[InternshipPeriod] = relationship(
        "InternshipPeriod", back_populates="internships"
    )
    mentor_assignments: Mapped[list[MentorAssignment]] = relationship(
        "MentorAssignment", back_populates="internship", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="internship", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[Evaluation]] = relationship(
        "Evaluation", back_populates="internship", cascade="all, delete-orphan"
    )
    lifecycle_requests: Mapped[list[LifecycleRequest]] = relationship(
        "LifecycleRequest", back_populates="internship", cascade="all, delete-orphan"
    )


class MentorAssignment(Base):
    __tablename__ = "mentor_assignments"
    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR assigned_at <= ended_at",
            name="ck_mentor_assignments_dates",
        ),
        Index("ix_mentor_assignments_internship_id", "internship_id"),
        Index("ix_mentor_assignments_mentor_id", "mentor_id"),
        Index(
            "uq_mentor_assignments_active_primary",
            "internship_id",
            unique=True,
            postgresql_where=(
                (mapped_column("is_primary") == True)  # noqa: E712
                & (mapped_column("ended_at").is_(None))
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False
    )
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    internship: Mapped[Internship] = relationship("Internship", back_populates="mentor_assignments")
    mentor: Mapped[User] = relationship(
        "User", back_populates="mentor_assignments", foreign_keys=[mentor_id]
    )
