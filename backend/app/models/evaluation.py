from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    EvaluationStatus,
    EvaluationType,
    LifecycleApprovalDecision,
    LifecycleRequestStatus,
    LifecycleRequestType,
)

if TYPE_CHECKING:
    from app.models.internship import Internship
    from app.models.user import User


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_evaluations_score"),
        CheckConstraint(
            "status != 'PUBLISHED' OR published_at IS NOT NULL", name="ck_evaluations_published_at"
        ),
        Index("ix_evaluations_internship_id", "internship_id"),
        Index("ix_evaluations_evaluator_id", "evaluator_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False
    )
    evaluator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_type: Mapped[EvaluationType] = mapped_column(
        Enum(EvaluationType, name="evaluation_type", native_enum=True), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status", native_enum=True),
        nullable=False,
        default=EvaluationStatus.DRAFT,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    internship: Mapped[Internship] = relationship("Internship", back_populates="evaluations")
    evaluator: Mapped[User] = relationship("User", foreign_keys=[evaluator_id])


class LifecycleRequest(Base):
    __tablename__ = "lifecycle_requests"
    __table_args__ = (
        Index("ix_lifecycle_requests_internship_id", "internship_id"),
        Index("ix_lifecycle_requests_status", "status"),
        Index(
            "uq_lifecycle_requests_pending",
            "internship_id",
            unique=True,
            postgresql_where=(mapped_column("status") == "PENDING"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), nullable=False
    )
    request_type: Mapped[LifecycleRequestType] = mapped_column(
        Enum(LifecycleRequestType, name="lifecycle_request_type", native_enum=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LifecycleRequestStatus] = mapped_column(
        Enum(LifecycleRequestStatus, name="lifecycle_request_status", native_enum=True),
        nullable=False,
        default=LifecycleRequestStatus.PENDING,
    )

    # Relationships
    internship: Mapped[Internship] = relationship("Internship", back_populates="lifecycle_requests")
    approvals: Mapped[list[LifecycleApproval]] = relationship(
        "LifecycleApproval", back_populates="request", cascade="all, delete-orphan"
    )


class LifecycleApproval(Base):
    __tablename__ = "lifecycle_approvals"
    __table_args__ = (
        Index("ix_lifecycle_approvals_request_id", "request_id"),
        Index("ix_lifecycle_approvals_approver_id", "approver_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lifecycle_requests.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[LifecycleApprovalDecision] = mapped_column(
        Enum(LifecycleApprovalDecision, name="lifecycle_approval_decision", native_enum=True),
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    request: Mapped[LifecycleRequest] = relationship("LifecycleRequest", back_populates="approvals")
    approver: Mapped[User] = relationship("User")
