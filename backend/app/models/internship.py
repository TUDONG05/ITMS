from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Internship(Base):
    __tablename__ = "dot_thuc_tap"
    __table_args__ = (
        CheckConstraint("ngay_ket_thuc >= ngay_bat_dau", name="ck_internships_dates"),
        CheckConstraint(
            "status IN ('DRAFT', 'OPEN', 'ONGOING', 'COMPLETED', 'CANCELLED')",
            name="ck_internships_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("ten", String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column("mo_ta", Text, nullable=True)
    start_date: Mapped[date] = mapped_column("ngay_bat_dau", Date, nullable=False)
    end_date: Mapped[date] = mapped_column("ngay_ket_thuc", Date, nullable=False)
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


class InternshipMember(Base):
    __tablename__ = "thanh_vien_thuc_tap"
    __table_args__ = (
        UniqueConstraint(
            "dot_thuc_tap_id", "thuc_tap_sinh_id", name="uq_internship_members_intern"
        ),
        CheckConstraint(
            "ngay_ket_thuc IS NULL OR ngay_bat_dau IS NULL OR ngay_ket_thuc >= ngay_bat_dau",
            name="ck_internship_members_dates",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'EXTENDED', 'STOPPED', 'COMPLETED')",
            name="ck_internship_members_status",
        ),
        Index("ix_internship_members_internship_id", "dot_thuc_tap_id"),
        Index("ix_internship_members_intern_id", "thuc_tap_sinh_id"),
        Index("ix_internship_members_mentor_id", "nguoi_huong_dan_id"),
        Index("ix_internship_members_roadmap_id", "lo_trinh_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_id: Mapped[uuid.UUID] = mapped_column(
        "dot_thuc_tap_id",
        UUID(as_uuid=True),
        ForeignKey("dot_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    intern_id: Mapped[uuid.UUID] = mapped_column(
        "thuc_tap_sinh_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    mentor_id: Mapped[uuid.UUID | None] = mapped_column(
        "nguoi_huong_dan_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="SET NULL"),
        nullable=True,
    )
    roadmap_id: Mapped[uuid.UUID | None] = mapped_column(
        "lo_trinh_id",
        UUID(as_uuid=True),
        ForeignKey("lo_trinh_dao_tao.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column("ngay_bat_dau", Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column("ngay_ket_thuc", Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class InternshipRequest(Base):
    __tablename__ = "yeu_cau_thuc_tap"
    __table_args__ = (
        CheckConstraint(
            "loai IN ('EXTEND', 'STOP', 'COMPLETE')", name="ck_internship_requests_type"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')", name="ck_internship_requests_status"
        ),
        Index("ix_internship_requests_status", "status"),
        Index("ix_internship_requests_internship_member_id", "thanh_vien_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        "thanh_vien_id",
        UUID(as_uuid=True),
        ForeignKey("thanh_vien_thuc_tap.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        "nguoi_yeu_cau_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column("loai", String(20), nullable=False)
    reason: Mapped[str] = mapped_column("ly_do", Text, nullable=False)
    requested_end_date: Mapped[date | None] = mapped_column(
        "ngay_ket_thuc_de_xuat", Date, nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        "nguoi_duyet_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column("ghi_chu_duyet", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
