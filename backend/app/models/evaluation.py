from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.internship import InternshipMember
    from app.models.user import User


class EvaluationCriteria(Base):
    __tablename__ = "evaluation_criteria"
    __table_args__ = (Index("ix_evaluation_criteria_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
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


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        Index("ix_evaluations_member_id", "internship_member_id"),
        Index("ix_evaluations_mentor_id", "mentor_id"),
        Index("ix_evaluations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PERIODIC")
    criteria_scores: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    member: Mapped[InternshipMember] = relationship(
        "InternshipMember", back_populates="evaluations"
    )
    mentor: Mapped[User] = relationship(
        "User", back_populates="evaluations_given", foreign_keys=[mentor_id]
    )


class InternshipRequest(Base):
    __tablename__ = "internship_requests"
    __table_args__ = (
        Index("ix_internship_requests_member_id", "internship_member_id"),
        Index("ix_internship_requests_requested_by", "requested_by"),
        Index("ix_internship_requests_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    member: Mapped[InternshipMember] = relationship("InternshipMember", back_populates="requests")
    requester: Mapped[User] = relationship(
        "User", back_populates="requests_made", foreign_keys=[requested_by]
    )
    reviewer: Mapped[User | None] = relationship(
        "User", back_populates="requests_reviewed", foreign_keys=[reviewed_by]
    )
