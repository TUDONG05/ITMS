import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import UserRole, UserStatus
from app.models.exam import Quiz, QuizAttempt
from app.models.interaction import Notification
from app.models.internship import Internship, InternshipMember
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.user import User
from app.schemas.mentor import (
    InternProfileSchema,
    InternRoadmapDetailSchema,
    InternshipBriefSchema,
    LearningContentProgressSchema,
    MentorAssignmentHistoryItem,
    MentorAssignRequestPayload,
    MentorBriefSchema,
    MentorInternDetailSchema,
    MentorInternListItem,
    MentorOverviewMetricsSchema,
    QuizAttemptDetailSchema,
    RoadmapPhaseDetailSchema,
)


class MentorService:
    @staticmethod
    def _find_member(db: Session, member_id_or_intern_id: uuid.UUID) -> InternshipMember | None:
        """Find internship member by either membership ID or intern user ID."""
        member = (
            db.query(InternshipMember).filter(InternshipMember.id == member_id_or_intern_id).first()
        )
        if not member:
            member = (
                db.query(InternshipMember)
                .filter(InternshipMember.intern_id == member_id_or_intern_id)
                .order_by(InternshipMember.created_at.desc())
                .first()
            )
        return member

    @staticmethod
    def _assert_mentor_access(current_user: User, member: InternshipMember) -> None:
        """Ensure mentor can only access their assigned interns."""
        if current_user.role == UserRole.MENTOR or current_user.role == "MENTOR":
            if member.mentor_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Intern is not assigned to this mentor",
                )

    @classmethod
    def get_mentor_interns(
        cls,
        db: Session,
        current_user: User,
        search: str | None = None,
        status_filter: str | None = None,
        internship_id: uuid.UUID | None = None,
    ) -> list[MentorInternListItem]:
        """List interns strictly scoped to the mentor's assignment."""
        query = db.query(InternshipMember).join(InternshipMember.intern)

        if current_user.role == UserRole.MENTOR or current_user.role == "MENTOR":
            query = query.filter(InternshipMember.mentor_id == current_user.id)

        if status_filter:
            query = query.filter(InternshipMember.status == status_filter)

        if internship_id:
            query = query.filter(InternshipMember.internship_id == internship_id)

        if search:
            pattern = f"%{search}%"
            query = query.filter((User.full_name.ilike(pattern)) | (User.email.ilike(pattern)))

        members = query.order_by(InternshipMember.created_at.desc()).all()
        results: list[MentorInternListItem] = []

        for member in members:
            # Internship info
            internship = db.query(Internship).filter(Internship.id == member.internship_id).first()
            internship_name = internship.name if internship else "Unknown Internship"

            # Roadmap info
            roadmap_name: str | None = None
            if member.roadmap_id:
                roadmap = db.query(Roadmap).filter(Roadmap.id == member.roadmap_id).first()
                if roadmap:
                    roadmap_name = roadmap.name

            # Mentor info
            mentor_name: str | None = None
            if member.mentor_id:
                mentor = db.query(User).filter(User.id == member.mentor_id).first()
                if mentor:
                    mentor_name = mentor.full_name

            # Learning progress percentage average
            avg_progress = (
                db.query(func.avg(LearningProgress.progress_percent))
                .filter(LearningProgress.internship_member_id == member.id)
                .scalar()
            )
            progress_percent = float(avg_progress or 0.0)

            # Quizzes passed count
            quizzes_passed = (
                db.query(func.count(QuizAttempt.id))
                .filter(
                    QuizAttempt.internship_member_id == member.id,
                    QuizAttempt.passed.is_(True),
                )
                .scalar()
                or 0
            )

            results.append(
                MentorInternListItem(
                    id=member.id,
                    intern_id=member.intern_id,
                    intern_name=member.intern.full_name,
                    intern_email=member.intern.email,
                    intern_phone=member.intern.phone,
                    intern_avatar_url=member.intern.avatar_url,
                    internship_id=member.internship_id,
                    internship_name=internship_name,
                    roadmap_id=member.roadmap_id,
                    roadmap_name=roadmap_name,
                    mentor_id=member.mentor_id,
                    mentor_name=mentor_name,
                    status=member.status,
                    start_date=member.start_date,
                    end_date=member.end_date,
                    progress_percent=round(progress_percent, 2),
                    quizzes_passed=quizzes_passed,
                    tasks_completed=0,
                    active_tasks=0,
                )
            )

        return results

    @classmethod
    def get_intern_roadmap(
        cls,
        db: Session,
        member: InternshipMember,
    ) -> InternRoadmapDetailSchema:
        """Retrieve roadmap structure and content progress for an intern."""
        if not member.roadmap_id:
            return InternRoadmapDetailSchema()

        roadmap = db.query(Roadmap).filter(Roadmap.id == member.roadmap_id).first()
        if not roadmap:
            return InternRoadmapDetailSchema()

        phases = (
            db.query(Phase)
            .filter(Phase.roadmap_id == member.roadmap_id)
            .order_by(Phase.order_no.asc())
            .all()
        )

        phase_schemas: list[RoadmapPhaseDetailSchema] = []
        for phase in phases:
            contents = (
                db.query(LearningContent)
                .filter(LearningContent.phase_id == phase.id)
                .order_by(LearningContent.order_no.asc())
                .all()
            )
            content_schemas: list[LearningContentProgressSchema] = []
            for content in contents:
                prog = (
                    db.query(LearningProgress)
                    .filter(
                        LearningProgress.internship_member_id == member.id,
                        LearningProgress.content_id == content.id,
                    )
                    .first()
                )
                content_schemas.append(
                    LearningContentProgressSchema(
                        id=content.id,
                        title=content.title,
                        type=content.type,
                        order_no=content.order_no,
                        progress_percent=float(prog.progress_percent) if prog else 0.0,
                        status=prog.status if prog else "NOT_STARTED",
                        completed_at=prog.completed_at if prog else None,
                    )
                )

            phase_schemas.append(
                RoadmapPhaseDetailSchema(
                    id=phase.id,
                    name=phase.name,
                    order_no=phase.order_no,
                    description=phase.description,
                    contents=content_schemas,
                )
            )

        return InternRoadmapDetailSchema(
            roadmap_id=roadmap.id,
            roadmap_name=roadmap.name,
            description=roadmap.description,
            phases=phase_schemas,
        )

    @classmethod
    def get_intern_quizzes(
        cls,
        db: Session,
        member: InternshipMember,
    ) -> list[QuizAttemptDetailSchema]:
        """Retrieve quiz attempts and scores for an intern."""
        attempts = (
            db.query(QuizAttempt, Quiz.title)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .filter(QuizAttempt.internship_member_id == member.id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )

        results: list[QuizAttemptDetailSchema] = []
        for attempt, quiz_title in attempts:
            results.append(
                QuizAttemptDetailSchema(
                    id=attempt.id,
                    quiz_id=attempt.quiz_id,
                    quiz_title=quiz_title,
                    attempt_no=attempt.attempt_no,
                    score=float(attempt.score) if attempt.score is not None else None,
                    passed=attempt.passed,
                    started_at=attempt.started_at,
                    submitted_at=attempt.submitted_at,
                )
            )
        return results

    @classmethod
    def get_intern_detail(
        cls,
        db: Session,
        member_id_or_intern_id: uuid.UUID,
        current_user: User,
    ) -> MentorInternDetailSchema:
        """Retrieve complete intern profile, roadmap, quizzes, and history."""
        member = cls._find_member(db, member_id_or_intern_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship member not found",
            )

        cls._assert_mentor_access(current_user, member)

        intern = member.intern
        internship = db.query(Internship).filter(Internship.id == member.internship_id).first()
        mentor = (
            db.query(User).filter(User.id == member.mentor_id).first() if member.mentor_id else None
        )

        roadmap_detail = cls.get_intern_roadmap(db, member)
        quiz_attempts = cls.get_intern_quizzes(db, member)
        assignment_history = cls.get_assignment_history(db, current_user, member_id=member.id)

        # Collect flat list of learning progress
        flat_progress: list[LearningContentProgressSchema] = []
        for phase in roadmap_detail.phases:
            flat_progress.extend(phase.contents)

        return MentorInternDetailSchema(
            id=member.id,
            intern=InternProfileSchema(
                id=intern.id,
                full_name=intern.full_name,
                email=intern.email,
                phone=intern.phone,
                avatar_url=intern.avatar_url,
                status=intern.status,
            ),
            internship=InternshipBriefSchema(
                id=internship.id if internship else member.internship_id,
                name=internship.name if internship else "Unknown",
                status=internship.status if internship else "UNKNOWN",
                start_date=internship.start_date if internship else None,
                end_date=internship.end_date if internship else None,
            ),
            mentor=MentorBriefSchema(
                id=mentor.id,
                full_name=mentor.full_name,
                email=mentor.email,
                phone=mentor.phone,
                avatar_url=mentor.avatar_url,
            )
            if mentor
            else None,
            roadmap=roadmap_detail,
            learning_progress=flat_progress,
            quiz_attempts=quiz_attempts,
            assignment_history=assignment_history,
            start_date=member.start_date,
            end_date=member.end_date,
            status=member.status,
        )

    @classmethod
    def assign_or_change_mentor(
        cls,
        db: Session,
        payload: MentorAssignRequestPayload,
        current_user: User,
    ) -> MentorAssignmentHistoryItem:
        """Assign or change primary mentor for an intern.
        Record durable audit record in database.
        """
        member = db.query(InternshipMember).filter(InternshipMember.id == payload.member_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship member not found",
            )

        # Mentor RBAC boundary: mentor can only reassign their own intern
        if current_user.role == UserRole.MENTOR or current_user.role == "MENTOR":
            if member.mentor_id is not None and member.mentor_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentor cannot reassign an intern assigned to another mentor",
                )
            if member.mentor_id is None and payload.mentor_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentor cannot assign an unassigned intern to someone else",
                )

        new_mentor = (
            db.query(User)
            .filter(User.id == payload.mentor_id, User.role == UserRole.MENTOR)
            .first()
        )
        if not new_mentor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New mentor not found or is not a mentor",
            )
        if new_mentor.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected mentor account is not active",
            )

        old_mentor_id = member.mentor_id
        old_mentor = (
            db.query(User).filter(User.id == old_mentor_id).first() if old_mentor_id else None
        )
        old_mentor_name = old_mentor.full_name if old_mentor else None

        action = "CHANGE" if old_mentor_id is not None else "ASSIGN"

        # Apply update to membership
        member.mentor_id = new_mentor.id
        member.updated_at = datetime.now(UTC)

        intern_user = db.query(User).filter(User.id == member.intern_id).first()
        intern_name = intern_user.full_name if intern_user else "Intern"
        changed_at = datetime.now(UTC)

        history_payload = {
            "action": action,
            "member_id": str(member.id),
            "intern_id": str(member.intern_id),
            "intern_name": intern_name,
            "old_mentor_id": str(old_mentor_id) if old_mentor_id else None,
            "old_mentor_name": old_mentor_name,
            "new_mentor_id": str(new_mentor.id),
            "new_mentor_name": new_mentor.full_name,
            "changed_by_id": str(current_user.id),
            "changed_by_name": current_user.full_name,
            "changed_at": changed_at.isoformat(),
            "note": payload.note,
        }

        notif_content = (
            payload.note
            or f"{action}: {intern_name} -> {new_mentor.full_name} by {current_user.full_name}"
        )
        notif = Notification(
            title=f"MENTOR_{action}",
            content=notif_content,
            target_type="USER",
            target_data=[history_payload],
            created_by=current_user.id,
            created_at=changed_at,
        )
        db.add(notif)
        db.commit()
        db.refresh(member)

        return MentorAssignmentHistoryItem(
            action=action,
            member_id=member.id,
            intern_id=member.intern_id,
            intern_name=intern_name,
            old_mentor_id=old_mentor_id,
            old_mentor_name=old_mentor_name,
            new_mentor_id=new_mentor.id,
            new_mentor_name=new_mentor.full_name,
            changed_by_id=current_user.id,
            changed_by_name=current_user.full_name,
            changed_at=changed_at,
            note=payload.note,
        )

    @classmethod
    def get_assignment_history(
        cls,
        db: Session,
        current_user: User,
        member_id: uuid.UUID | None = None,
    ) -> list[MentorAssignmentHistoryItem]:
        """Query assignment history audit logs directly from database (thong_bao table)."""
        if (current_user.role == UserRole.MENTOR or current_user.role == "MENTOR") and member_id:
            member = cls._find_member(db, member_id)
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Internship member not found",
                )
            cls._assert_mentor_access(current_user, member)

        notifications = (
            db.query(Notification)
            .filter(Notification.title.in_(["MENTOR_ASSIGN", "MENTOR_CHANGE"]))
            .order_by(Notification.created_at.desc())
            .all()
        )

        filtered: list[MentorAssignmentHistoryItem] = []
        for notif in notifications:
            if not notif.target_data:
                continue
            items = (
                notif.target_data if isinstance(notif.target_data, list) else [notif.target_data]
            )
            for raw in items:
                if not isinstance(raw, dict):
                    continue

                raw_member_id = raw.get("member_id")
                if member_id and str(raw_member_id) != str(member_id):
                    continue

                if current_user.role == UserRole.MENTOR or current_user.role == "MENTOR":
                    is_related = raw.get("old_mentor_id") == str(current_user.id) or raw.get(
                        "new_mentor_id"
                    ) == str(current_user.id)
                    # If querying member-specific history, permission was already asserted above
                    if not is_related and not member_id:
                        continue

                changed_at_raw = raw.get("changed_at")
                parsed_date = (
                    datetime.fromisoformat(changed_at_raw)
                    if isinstance(changed_at_raw, str)
                    else notif.created_at
                )

                filtered.append(
                    MentorAssignmentHistoryItem(
                        action=raw.get("action", "ASSIGN"),
                        member_id=uuid.UUID(str(raw["member_id"])),
                        intern_id=uuid.UUID(str(raw["intern_id"])),
                        intern_name=raw.get("intern_name", "Intern"),
                        old_mentor_id=uuid.UUID(str(raw["old_mentor_id"]))
                        if raw.get("old_mentor_id")
                        else None,
                        old_mentor_name=raw.get("old_mentor_name"),
                        new_mentor_id=uuid.UUID(str(raw["new_mentor_id"])),
                        new_mentor_name=raw.get("new_mentor_name", "Mentor"),
                        changed_by_id=uuid.UUID(str(raw["changed_by_id"])),
                        changed_by_name=raw.get("changed_by_name", "User"),
                        changed_at=parsed_date,
                        note=raw.get("note"),
                    )
                )

        return filtered

    @classmethod
    def get_mentor_overview(
        cls,
        db: Session,
        current_user: User,
    ) -> MentorOverviewMetricsSchema:
        """Aggregate high-level overview metrics for the mentor strictly within their scope."""
        interns = cls.get_mentor_interns(db, current_user)
        total = len(interns)
        active = sum(1 for i in interns if i.status == "ACTIVE")
        completed = sum(1 for i in interns if i.status == "COMPLETED")
        avg_prog = (sum(i.progress_percent for i in interns) / total) if total > 0 else 0.0
        total_quizzes = sum(i.quizzes_passed for i in interns)

        return MentorOverviewMetricsSchema(
            total_interns=total,
            active_interns=active,
            completed_interns=completed,
            avg_progress=round(avg_prog, 2),
            total_quizzes_passed=total_quizzes,
            recent_interns=interns[:5],
        )
