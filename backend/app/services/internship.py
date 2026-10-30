import uuid
from datetime import UTC, date, datetime, time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole
from app.models.internship import (
    Internship,
    InternshipApplication,
    InternshipMember,
    InternshipRequest,
)
from app.models.roadmap import Roadmap
from app.models.user import User
from app.schemas.internship import (
    BatchResult,
    BatchReviewPayload,
    InternshipApplicationCreate,
    InternshipApplicationRead,
    InternshipApplicationReview,
    InternshipCreate,
    InternshipMemberCreate,
    InternshipMemberUpdate,
    InternshipProposalCreate,
    InternshipRequestRead,
    InternshipRequestReview,
    InternshipStatusHistoryItem,
    InternshipUpdate,
)


class InternshipService:
    @staticmethod
    def _validate_roadmap(db: Session, roadmap_id: uuid.UUID | None) -> uuid.UUID | None:
        if roadmap_id is None:
            return None
        roadmap = db.get(Roadmap, roadmap_id)
        if roadmap is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found",
            )
        if roadmap.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ACTIVE roadmaps can be assigned to an internship",
            )
        return roadmap.id

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

        roadmap_id = InternshipService._validate_roadmap(db, data.roadmap_id)
        internship = Internship(
            name=data.name,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            roadmap_id=roadmap_id,
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
        query = (
            select(Internship)
            .options(selectinload(Internship.members))
            .order_by(Internship.created_at.desc())
        )
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
        update_data = data.model_dump(exclude_unset=True)
        if "roadmap_id" in update_data:
            roadmap_id = InternshipService._validate_roadmap(db, data.roadmap_id)
            internship.roadmap_id = roadmap_id
            for member in internship.members:
                member.roadmap_id = roadmap_id

        db.commit()
        db.refresh(internship)
        return internship

    @staticmethod
    def add_member_to_internship(
        db: Session,
        internship_id: uuid.UUID,
        data: InternshipMemberCreate,
    ) -> InternshipMember:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Chức năng thêm trực tiếp thực tập sinh đã bị loại bỏ. "
                "Thực tập sinh phải tự nộp đơn đăng ký và chờ Admin phê duyệt."
            ),
        )

    @staticmethod
    def get_members_by_internship(
        db: Session,
        internship_id: uuid.UUID,
        search: str | None = None,
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
        if search:
            stmt = stmt.join(InternshipMember.intern).where(
                User.full_name.ilike(f"%{search.strip()}%")
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

    @staticmethod
    def update_member(
        db: Session,
        member_id: uuid.UUID,
        payload: InternshipMemberUpdate,
    ) -> InternshipMember:
        member = InternshipService.get_member_by_id(db, member_id)

        update_data = payload.model_dump(exclude_unset=True)

        if "mentor_id" in update_data:
            mentor_id = update_data["mentor_id"]
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

        new_start = update_data.get("start_date", member.start_date)
        new_end = update_data.get("end_date", member.end_date)
        if new_start and new_end and new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must not be before start_date",
            )

        if "start_date" in update_data:
            member.start_date = update_data["start_date"]
        if "end_date" in update_data:
            member.end_date = update_data["end_date"]
        if "status" in update_data and update_data["status"] is not None:
            member.status = update_data["status"]
        if "roadmap_id" in update_data:
            member.roadmap_id = update_data["roadmap_id"]

        db.commit()
        db.refresh(member)
        return InternshipService.get_member_by_id(db, member_id)

    @staticmethod
    def enrich_request(db: Session, req: InternshipRequest) -> InternshipRequestRead:
        data = InternshipRequestRead.model_validate(req)
        member = db.get(InternshipMember, req.internship_member_id)
        if member:
            intern = db.get(User, member.intern_id)
            if intern:
                data.intern_id = intern.id
                data.intern_name = intern.full_name
                data.intern_email = intern.email
            internship = db.get(Internship, member.internship_id)
            if internship:
                data.internship_id = internship.id
                data.internship_name = internship.name
            mentor = db.get(User, req.requested_by)
            if mentor:
                data.mentor_name = mentor.full_name
        return data

    @staticmethod
    def get_requests(
        db: Session,
        status_filter: str | None = None,
        type_filter: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[InternshipRequestRead]:
        stmt = select(InternshipRequest).order_by(InternshipRequest.created_at.desc())

        if status_filter:
            stmt = stmt.where(InternshipRequest.status == status_filter)
        if type_filter:
            stmt = stmt.where(InternshipRequest.type == type_filter)
        if start_date:
            stmt = stmt.where(
                InternshipRequest.created_at >= datetime.combine(start_date, time.min)
            )
        if end_date:
            stmt = stmt.where(InternshipRequest.created_at <= datetime.combine(end_date, time.max))

        requests = list(db.scalars(stmt).all())
        return [InternshipService.enrich_request(db, r) for r in requests]

    @staticmethod
    def create_proposal(
        db: Session,
        payload: InternshipProposalCreate,
        current_user: User,
    ) -> InternshipRequestRead:
        member = InternshipService.get_member_by_id(db, payload.member_id)

        if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN) and str(
            current_user.role
        ) not in ("MENTOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền tạo đề xuất cho thực tập sinh",
            )

        # Mentor permission assertion
        if current_user.role == UserRole.MENTOR or str(current_user.role) == "MENTOR":
            if member.mentor_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentor không phụ trách thực tập sinh này",
                )

        prop_type = str(payload.type).upper()
        if prop_type == "TERMINATE":
            prop_type = "STOP"

        # BR-10: Chỉ một yêu cầu gia hạn đang chờ
        if prop_type == "EXTEND":
            existing_pending_extend = db.scalar(
                select(InternshipRequest).where(
                    InternshipRequest.internship_member_id == member.id,
                    InternshipRequest.type == "EXTEND",
                    InternshipRequest.status == "PENDING",
                )
            )
            if existing_pending_extend is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Đã có yêu cầu gia hạn đang chờ xử lý.",
                )
            # Date validation
            if payload.requested_end_date:
                if member.start_date and payload.requested_end_date <= member.start_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ngày gia hạn đề xuất phải sau ngày bắt đầu thực tập",
                    )
                if member.end_date and payload.requested_end_date <= member.end_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ngày gia hạn đề xuất phải sau ngày kết thúc hiện tại",
                    )
        else:
            existing_same_pending = db.scalar(
                select(InternshipRequest).where(
                    InternshipRequest.internship_member_id == member.id,
                    InternshipRequest.type == prop_type,
                    InternshipRequest.status == "PENDING",
                )
            )
            if existing_same_pending is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Đã có yêu cầu {prop_type} đang chờ xử lý.",
                )

        req = InternshipRequest(
            internship_member_id=member.id,
            requested_by=current_user.id,
            type=prop_type,
            reason=payload.reason,
            requested_end_date=payload.requested_end_date if prop_type == "EXTEND" else None,
            status="PENDING",
            created_at=datetime.now(UTC),
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return InternshipService.enrich_request(db, req)

    @staticmethod
    def get_member_status_history(
        db: Session,
        member_id: uuid.UUID,
        current_user: User,
    ) -> list[InternshipStatusHistoryItem]:
        member = InternshipService.get_member_by_id(db, member_id)

        # Permission check: Mentor must be assigned mentor or user is Admin
        if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN) and str(
            current_user.role
        ) not in ("MENTOR", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền xem lịch sử của Intern này",
            )

        if current_user.role == UserRole.MENTOR or str(current_user.role) == "MENTOR":
            if member.mentor_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentor không có quyền xem lịch sử của Intern này",
                )

        # Initial creation event
        items: list[InternshipStatusHistoryItem] = [
            InternshipStatusHistoryItem(
                id=member.id,
                action="INITIAL",
                from_status=None,
                to_status="ACTIVE",
                requested_by_name="Hệ thống",
                reviewed_by_name=None,
                changed_at=member.created_at,
                reason="Bắt đầu thực tập",
                review_note=None,
                proposal_status=None,
                requested_end_date=member.end_date,
            )
        ]

        requests = list(
            db.scalars(
                select(InternshipRequest)
                .where(InternshipRequest.internship_member_id == member.id)
                .order_by(InternshipRequest.created_at.asc())
            ).all()
        )

        current_hist_status = "ACTIVE"
        for r in requests:
            requester = db.get(User, r.requested_by)
            reviewer = db.get(User, r.reviewed_by) if r.reviewed_by else None

            if r.status == "APPROVED":
                next_status = (
                    InternshipMemberStatus.EXTENDED
                    if r.type == "EXTEND"
                    else (
                        InternshipMemberStatus.STOPPED
                        if r.type == "STOP"
                        else InternshipMemberStatus.COMPLETED
                    )
                )
                items.append(
                    InternshipStatusHistoryItem(
                        id=r.id,
                        action=r.type,
                        from_status=current_hist_status,
                        to_status=next_status,
                        requested_by_name=requester.full_name if requester else "Mentor",
                        reviewed_by_name=reviewer.full_name if reviewer else "Manager",
                        changed_at=r.reviewed_at or r.created_at,
                        reason=r.reason,
                        review_note=r.review_note,
                        proposal_status="APPROVED",
                        requested_end_date=r.requested_end_date,
                    )
                )
                current_hist_status = next_status
            elif r.status == "REJECTED":
                items.append(
                    InternshipStatusHistoryItem(
                        id=r.id,
                        action=r.type,
                        from_status=current_hist_status,
                        to_status=current_hist_status,
                        requested_by_name=requester.full_name if requester else "Mentor",
                        reviewed_by_name=reviewer.full_name if reviewer else "Manager",
                        changed_at=r.reviewed_at or r.created_at,
                        reason=r.reason,
                        review_note=r.review_note,
                        proposal_status="REJECTED",
                        requested_end_date=r.requested_end_date,
                    )
                )
            else:  # PENDING
                items.append(
                    InternshipStatusHistoryItem(
                        id=r.id,
                        action=r.type,
                        from_status=current_hist_status,
                        to_status=current_hist_status,
                        requested_by_name=requester.full_name if requester else "Mentor",
                        reviewed_by_name=None,
                        changed_at=r.created_at,
                        reason=r.reason,
                        review_note=None,
                        proposal_status="PENDING",
                        requested_end_date=r.requested_end_date,
                    )
                )

        items.sort(key=lambda x: x.changed_at, reverse=True)
        return items

    @staticmethod
    def get_mentor_proposals(
        db: Session,
        current_user: User,
        status_filter: str | None = None,
    ) -> list[InternshipRequestRead]:
        if current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN":
            stmt = select(InternshipRequest).order_by(InternshipRequest.created_at.desc())
        else:
            stmt = (
                select(InternshipRequest)
                .join(
                    InternshipMember,
                    InternshipRequest.internship_member_id == InternshipMember.id,
                )
                .where(
                    (InternshipRequest.requested_by == current_user.id)
                    | (InternshipMember.mentor_id == current_user.id)
                )
                .order_by(InternshipRequest.created_at.desc())
            )
        if status_filter:
            stmt = stmt.where(InternshipRequest.status == status_filter)
        requests = list(db.scalars(stmt).all())
        return [InternshipService.enrich_request(db, r) for r in requests]

    @staticmethod
    def review_request(
        db: Session,
        request_id: uuid.UUID,
        payload: InternshipRequestReview,
        reviewer_id: uuid.UUID,
    ) -> InternshipRequestRead:
        stmt = select(InternshipRequest).where(InternshipRequest.id == request_id)
        req = db.scalar(stmt)
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        if req.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request has already been processed",
            )
        if payload.status not in ("APPROVED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be APPROVED or REJECTED",
            )

        req.status = payload.status
        req.review_note = payload.review_note
        req.reviewed_by = reviewer_id
        req.reviewed_at = datetime.now(UTC)

        # Cập nhật trạng thái thành viên nếu APPROVED
        if payload.status == "APPROVED":
            member_stmt = select(InternshipMember).where(
                InternshipMember.id == req.internship_member_id
            )
            member = db.scalar(member_stmt)
            if member:
                if req.type == "EXTEND":
                    member.status = InternshipMemberStatus.EXTENDED
                    if req.requested_end_date:
                        member.end_date = req.requested_end_date
                elif req.type == "STOP":
                    member.status = InternshipMemberStatus.STOPPED
                elif req.type == "COMPLETE":
                    member.status = InternshipMemberStatus.COMPLETED
                member.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(req)
        return InternshipService.enrich_request(db, req)

    @staticmethod
    def enrich_application(db: Session, app: InternshipApplication) -> InternshipApplicationRead:
        internship_name = app.internship.name if app.internship else None
        if not internship_name and app.internship_id:
            it = db.get(Internship, app.internship_id)
            if it:
                internship_name = it.name

        intern_name = app.intern.full_name if app.intern else None
        intern_email = app.intern.email if app.intern else None
        if (not intern_name or not intern_email) and app.intern_id:
            u = db.get(User, app.intern_id)
            if u:
                intern_name = u.full_name
                intern_email = u.email

        reviewer_name = app.reviewer.full_name if app.reviewer else None
        if not reviewer_name and app.reviewed_by:
            rev = db.get(User, app.reviewed_by)
            if rev:
                reviewer_name = rev.full_name

        return InternshipApplicationRead(
            id=app.id,
            internship_id=app.internship_id,
            intern_id=app.intern_id,
            status=app.status,
            reason=app.reason,
            reviewed_by=app.reviewed_by,
            review_note=app.review_note,
            created_at=app.created_at,
            reviewed_at=app.reviewed_at,
            internship_name=internship_name,
            intern_name=intern_name,
            intern_email=intern_email,
            reviewer_name=reviewer_name,
        )

    @staticmethod
    def get_open_internships(db: Session) -> list[Internship]:
        stmt = (
            select(Internship)
            .where(Internship.status == InternshipStatus.OPEN)
            .order_by(Internship.start_date.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def apply_internship(
        db: Session,
        internship_id: uuid.UUID,
        intern_id: uuid.UUID,
        data: InternshipApplicationCreate,
    ) -> InternshipApplicationRead:
        internship = db.get(Internship, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Đợt thực tập không tồn tại.",
            )

        if internship.status != InternshipStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ có thể đăng ký các đợt thực tập đang mở (OPEN).",
            )

        # Kiểm tra intern đã là thành viên trong đợt chưa
        mem_stmt = select(InternshipMember).where(
            InternshipMember.internship_id == internship_id,
            InternshipMember.intern_id == intern_id,
        )
        if db.scalar(mem_stmt) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bạn đã là thành viên của đợt thực tập này.",
            )

        # Kiểm tra đơn đăng ký hiện có
        app_stmt = select(InternshipApplication).where(
            InternshipApplication.internship_id == internship_id,
            InternshipApplication.intern_id == intern_id,
        )
        existing_app = db.scalar(app_stmt)
        if existing_app:
            if existing_app.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bạn đã gửi đơn đăng ký cho đợt thực tập này và đang chờ duyệt.",
                )
            elif existing_app.status == "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Đơn đăng ký của bạn cho đợt này đã được phê duyệt.",
                )
            elif existing_app.status == "REJECTED":
                # Nộp lại đơn mới
                clean_reason = data.reason.strip() if data.reason and data.reason.strip() else None
                existing_app.status = "PENDING"
                existing_app.reason = clean_reason
                existing_app.reviewed_by = None
                existing_app.review_note = None
                existing_app.reviewed_at = None
                existing_app.created_at = datetime.now(UTC)
                db.commit()
                db.refresh(existing_app)
                return InternshipService.enrich_application(db, existing_app)

        clean_reason = data.reason.strip() if data.reason and data.reason.strip() else None
        new_app = InternshipApplication(
            internship_id=internship_id,
            intern_id=intern_id,
            reason=clean_reason,
            status="PENDING",
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)
        return InternshipService.enrich_application(db, new_app)

    @staticmethod
    def get_my_applications(db: Session, intern_id: uuid.UUID) -> list[InternshipApplicationRead]:
        stmt = (
            select(InternshipApplication)
            .where(InternshipApplication.intern_id == intern_id)
            .options(
                selectinload(InternshipApplication.internship),
                selectinload(InternshipApplication.intern),
                selectinload(InternshipApplication.reviewer),
            )
            .order_by(InternshipApplication.created_at.desc())
        )
        apps = list(db.scalars(stmt).all())
        return [InternshipService.enrich_application(db, a) for a in apps]

    @staticmethod
    def get_applications(
        db: Session,
        status_filter: str | None = None,
        internship_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> list[InternshipApplicationRead]:
        stmt = (
            select(InternshipApplication)
            .join(InternshipApplication.intern)
            .options(
                selectinload(InternshipApplication.internship),
                selectinload(InternshipApplication.intern),
                selectinload(InternshipApplication.reviewer),
            )
            .order_by(InternshipApplication.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(InternshipApplication.status == status_filter)
        if internship_id:
            stmt = stmt.where(InternshipApplication.internship_id == internship_id)
        if search:
            stmt = stmt.where(
                User.full_name.ilike(f"%{search.strip()}%")
                | User.email.ilike(f"%{search.strip()}%")
            )
        apps = list(db.scalars(stmt).all())
        return [InternshipService.enrich_application(db, a) for a in apps]

    @staticmethod
    def get_application_by_id(db: Session, app_id: uuid.UUID) -> InternshipApplicationRead:
        stmt = (
            select(InternshipApplication)
            .where(InternshipApplication.id == app_id)
            .options(
                selectinload(InternshipApplication.internship),
                selectinload(InternshipApplication.intern),
                selectinload(InternshipApplication.reviewer),
            )
        )
        app = db.scalar(stmt)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Đơn đăng ký không tồn tại.",
            )
        return InternshipService.enrich_application(db, app)

    @staticmethod
    def review_application(
        db: Session,
        app_id: uuid.UUID,
        payload: InternshipApplicationReview,
        reviewer_id: uuid.UUID,
    ) -> InternshipApplicationRead:
        app = db.scalar(
            select(InternshipApplication)
            .where(InternshipApplication.id == app_id)
            .with_for_update()
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Đơn đăng ký không tồn tại.",
            )
        if app.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Đơn đăng ký đã được xử lý trước đó (trạng thái: {app.status}).",
            )

        if payload.status == "APPROVED":
            internship = db.get(Internship, app.internship_id)
            if not internship or internship.status == InternshipStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Đợt thực tập đã bị hủy hoặc không còn khả dụng.",
                )

            # Chống thêm trùng (concurrency check)
            dup_check = (
                select(InternshipMember)
                .where(
                    InternshipMember.internship_id == app.internship_id,
                    InternshipMember.intern_id == app.intern_id,
                )
                .with_for_update()
            )
            if db.scalar(dup_check) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Thực tập sinh đã là thành viên của đợt thực tập này.",
                )

            # Thêm vào thành viên chính thức, kế thừa lộ trình từ đợt
            new_member = InternshipMember(
                internship_id=app.internship_id,
                intern_id=app.intern_id,
                roadmap_id=internship.roadmap_id,
                start_date=internship.start_date,
                end_date=internship.end_date,
                status=InternshipMemberStatus.ACTIVE,
            )
            db.add(new_member)

        app.status = payload.status
        app.reviewed_by = reviewer_id
        app.review_note = payload.review_note
        app.reviewed_at = datetime.now(UTC)

        db.commit()
        db.refresh(app)
        return InternshipService.enrich_application(db, app)

    @staticmethod
    def batch_review_applications(
        db: Session,
        payload: BatchReviewPayload,
        reviewer_id: uuid.UUID,
    ) -> BatchResult:
        if not payload.ids:
            return BatchResult(processed_count=0, message="Không có đơn đăng ký nào được chọn.")

        processed = 0
        now = datetime.now(UTC)
        for app_id in payload.ids:
            app = db.scalar(
                select(InternshipApplication)
                .where(InternshipApplication.id == app_id)
                .with_for_update()
            )
            if not app or app.status != "PENDING":
                continue

            if payload.status == "APPROVED":
                internship = db.get(Internship, app.internship_id)
                if not internship or internship.status == InternshipStatus.CANCELLED:
                    continue

                dup = db.scalar(
                    select(InternshipMember)
                    .where(
                        InternshipMember.internship_id == app.internship_id,
                        InternshipMember.intern_id == app.intern_id,
                    )
                    .with_for_update()
                )
                if dup is not None:
                    continue

                new_member = InternshipMember(
                    internship_id=app.internship_id,
                    intern_id=app.intern_id,
                    roadmap_id=internship.roadmap_id,
                    start_date=internship.start_date,
                    end_date=internship.end_date,
                    status=InternshipMemberStatus.ACTIVE,
                )
                db.add(new_member)

            app.status = payload.status
            app.reviewed_by = reviewer_id
            app.review_note = payload.review_note
            app.reviewed_at = now
            processed += 1

        db.commit()
        action_text = "phê duyệt" if payload.status == "APPROVED" else "từ chối"
        return BatchResult(
            processed_count=processed,
            message=f"Đã {action_text} thành công {processed} đơn đăng ký.",
        )

    @staticmethod
    def approve_all_applications(db: Session, reviewer_id: uuid.UUID) -> BatchResult:
        stmt = (
            select(InternshipApplication.id)
            .where(InternshipApplication.status == "PENDING")
            .with_for_update()
        )
        pending_ids = list(db.scalars(stmt).all())
        payload = BatchReviewPayload(ids=pending_ids, status="APPROVED")
        return InternshipService.batch_review_applications(db, payload, reviewer_id)

    @staticmethod
    def batch_review_requests(
        db: Session,
        payload: BatchReviewPayload,
        reviewer_id: uuid.UUID,
    ) -> BatchResult:
        if not payload.ids:
            return BatchResult(processed_count=0, message="Không có yêu cầu nào được chọn.")

        processed = 0
        now = datetime.now(UTC)
        for req_id in payload.ids:
            req = db.scalar(
                select(InternshipRequest).where(InternshipRequest.id == req_id).with_for_update()
            )
            if not req or req.status != "PENDING":
                continue

            req.status = payload.status
            req.review_note = payload.review_note
            req.reviewed_by = reviewer_id
            req.reviewed_at = now

            if payload.status == "APPROVED":
                member = db.scalar(
                    select(InternshipMember)
                    .where(InternshipMember.id == req.internship_member_id)
                    .with_for_update()
                )
                if member:
                    if req.type == "EXTEND":
                        member.status = InternshipMemberStatus.EXTENDED
                        if req.requested_end_date:
                            member.end_date = req.requested_end_date
                    elif req.type == "STOP":
                        member.status = InternshipMemberStatus.STOPPED
                    elif req.type == "COMPLETE":
                        member.status = InternshipMemberStatus.COMPLETED
                    member.updated_at = now

            processed += 1

        db.commit()
        action_text = "phê duyệt" if payload.status == "APPROVED" else "từ chối"
        return BatchResult(
            processed_count=processed,
            message=f"Đã {action_text} thành công {processed} yêu cầu.",
        )

    @staticmethod
    def approve_all_requests(db: Session, reviewer_id: uuid.UUID) -> BatchResult:
        stmt = (
            select(InternshipRequest.id)
            .where(InternshipRequest.status == "PENDING")
            .with_for_update()
        )
        pending_ids = list(db.scalars(stmt).all())
        payload = BatchReviewPayload(ids=pending_ids, status="APPROVED")
        return InternshipService.batch_review_requests(db, payload, reviewer_id)
