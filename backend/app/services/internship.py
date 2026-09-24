import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import InternshipStatus, UserRole
from app.models.internship import Internship, InternshipMember
from app.models.user import User
from app.schemas.internship import (
    InternshipCreate,
    InternshipMemberCreate,
    InternshipUpdate,
)


class InternshipService:
    @staticmethod
    def create_internship(
        db: Session,
        data: InternshipCreate,
        creator_id: uuid.UUID | None = None,
    ) -> Internship:
        if data.end_date < data.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must not be before start_date",
            )

        existing = db.scalar(select(Internship).where(Internship.name == data.name))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Internship with name '{data.name}' already exists",
            )

        internship = Internship(
            name=data.name,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            created_by=creator_id,
        )
        db.add(internship)
        db.commit()
        db.refresh(internship)
        return internship

    @staticmethod
    def get_internships(
        db: Session,
        status_filter: InternshipStatus | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Internship]:
        query = select(Internship).order_by(Internship.created_at.desc())
        if status_filter is not None:
            query = query.where(Internship.status == status_filter)
        if search:
            query = query.where(Internship.name.ilike(f"%{search.strip()}%"))
        query = query.offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def get_internship_by_id(db: Session, internship_id: uuid.UUID) -> Internship:
        stmt = (
            select(Internship)
            .where(Internship.id == internship_id)
            .options(selectinload(Internship.members))
        )
        internship = db.scalar(stmt)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found",
            )
        return internship

    @staticmethod
    def update_internship(
        db: Session,
        internship_id: uuid.UUID,
        data: InternshipUpdate,
    ) -> Internship:
        internship = InternshipService.get_internship_by_id(db, internship_id)

        new_start = data.start_date if data.start_date is not None else internship.start_date
        new_end = data.end_date if data.end_date is not None else internship.end_date
        if new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must not be before start_date",
            )

        if data.name is not None and data.name != internship.name:
            existing = db.scalar(select(Internship).where(Internship.name == data.name))
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Internship with name '{data.name}' already exists",
                )
            internship.name = data.name

        if data.description is not None:
            internship.description = data.description
        if data.start_date is not None:
            internship.start_date = data.start_date
        if data.end_date is not None:
            internship.end_date = data.end_date
        if data.status is not None:
            internship.status = data.status

        db.commit()
        db.refresh(internship)
        return internship

    @staticmethod
    def add_member_to_internship(
        db: Session,
        internship_id: uuid.UUID,
        data: InternshipMemberCreate,
    ) -> InternshipMember:
        InternshipService.get_internship_by_id(db, internship_id)

        # Validate intern exists and has role INTERN
        intern = db.get(User, data.intern_id)
        if not intern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intern user not found",
            )
        if intern.role != UserRole.INTERN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{data.intern_id}' does not have role INTERN",
            )

        # Check duplicate member in this internship
        dup_stmt = select(InternshipMember).where(
            InternshipMember.internship_id == internship_id,
            InternshipMember.intern_id == data.intern_id,
        )
        if db.scalar(dup_stmt) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Intern '{data.intern_id}' is already enrolled in this internship",
            )

        # Validate mentor if provided
        if data.mentor_id is not None:
            mentor = db.get(User, data.mentor_id)
            if not mentor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Mentor user not found",
                )
            if mentor.role != UserRole.MENTOR:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User '{data.mentor_id}' does not have role MENTOR",
                )

        if (
            data.start_date is not None
            and data.end_date is not None
            and data.end_date < data.start_date
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must not be before start_date",
            )

        member = InternshipMember(
            internship_id=internship_id,
            intern_id=data.intern_id,
            mentor_id=data.mentor_id,
            roadmap_id=data.roadmap_id,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
        )
        db.add(member)
        db.commit()

        # Re-fetch with relationships loaded
        return InternshipService.get_member_by_id(db, member.id)

    @staticmethod
    def get_members_by_internship(
        db: Session,
        internship_id: uuid.UUID,
    ) -> list[InternshipMember]:
        InternshipService.get_internship_by_id(db, internship_id)

        stmt = (
            select(InternshipMember)
            .where(InternshipMember.internship_id == internship_id)
            .options(
                selectinload(InternshipMember.intern),
                selectinload(InternshipMember.mentor),
            )
            .order_by(InternshipMember.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_member_by_id(db: Session, member_id: uuid.UUID) -> InternshipMember:
        stmt = (
            select(InternshipMember)
            .where(InternshipMember.id == member_id)
            .options(
                selectinload(InternshipMember.intern),
                selectinload(InternshipMember.mentor),
            )
        )
        member = db.scalar(stmt)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship member not found",
            )
        return member

    @staticmethod
    def assign_mentor_to_member(
        db: Session,
        member_id: uuid.UUID,
        mentor_id: uuid.UUID | None,
    ) -> InternshipMember:
        member = InternshipService.get_member_by_id(db, member_id)

        if mentor_id is not None:
            mentor = db.get(User, mentor_id)
            if not mentor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Mentor user not found",
                )
            if mentor.role != UserRole.MENTOR:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User '{mentor_id}' does not have role MENTOR",
                )

        member.mentor_id = mentor_id
        db.commit()
        db.refresh(member)
        return member
