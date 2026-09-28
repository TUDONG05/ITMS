from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.models.evaluation import Evaluation
from app.models.exam import QuizAttempt
from app.models.internship import Internship, InternshipMember, InternshipRequest
from app.models.roadmap import LearningProgress
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import (
    DashboardMetricRead,
    DashboardProgressRead,
    DashboardRead,
    DashboardRecentItemRead,
    DashboardTaskBreakdownRead,
)

OPEN_TASK_STATUSES = ("TODO", "IN_PROGRESS", "SUBMITTED", "REVISION_REQUIRED")
ACTIVE_MEMBER_STATUSES = (InternshipMemberStatus.ACTIVE, InternshipMemberStatus.EXTENDED)


class DashboardService:
    @staticmethod
    def build(
        db: Session, current_user: User, internship_id: uuid.UUID | None = None
    ) -> DashboardRead:
        if current_user.role == UserRole.ADMIN:
            return DashboardService._build_admin(db, internship_id)
        members = db.query(InternshipMember)
        if current_user.role == UserRole.MENTOR:
            return DashboardService._build_mentor(
                db, members.filter(InternshipMember.mentor_id == current_user.id)
            )
        return DashboardService._build_intern(
            db, members.filter(InternshipMember.intern_id == current_user.id)
        )

    @staticmethod
    def _build_admin(db: Session, internship_id: uuid.UUID | None) -> DashboardRead:
        internships = db.query(Internship)
        if internship_id is not None:
            internship = db.get(Internship, internship_id)
            if internship is None:
                raise LookupError("Internship not found")
            internships = internships.filter(Internship.id == internship.id)
        members = db.query(InternshipMember).filter(
            InternshipMember.internship_id.in_(internships.with_entities(Internship.id))
        )
        member_ids = members.with_entities(InternshipMember.id)
        active_members = members.filter(InternshipMember.status.in_(ACTIVE_MEMBER_STATUSES))
        tasks = DashboardService._tasks(db, member_ids)
        metrics = [
            DashboardMetricRead(
                key="active_interns",
                label="Thực tập sinh đang hoạt động",
                value=DashboardService._active_user_count(
                    active_members, InternshipMember.intern_id
                ),
            ),
            DashboardMetricRead(
                key="active_mentors",
                label="Mentor đang phụ trách",
                value=DashboardService._active_user_count(
                    active_members, InternshipMember.mentor_id
                ),
            ),
            DashboardMetricRead(
                key="ongoing_internships",
                label="Đợt thực tập đang diễn ra",
                value=internships.filter(
                    Internship.status.in_((InternshipStatus.OPEN, InternshipStatus.ONGOING))
                ).count(),
            ),
            DashboardMetricRead(
                key="pending_requests",
                label="Yêu cầu chờ duyệt",
                value=db.query(InternshipRequest)
                .filter(
                    InternshipRequest.internship_member_id.in_(member_ids),
                    InternshipRequest.status == "PENDING",
                )
                .count(),
            ),
            DashboardMetricRead(key="total_tasks", label="Tổng task", value=tasks.count()),
            DashboardMetricRead(
                key="published_evaluations",
                label="Đánh giá đã công bố",
                value=db.query(Evaluation)
                .filter(
                    Evaluation.internship_member_id.in_(member_ids),
                    Evaluation.status == "PUBLISHED",
                )
                .count(),
            ),
        ]
        return DashboardRead(
            role=UserRole.ADMIN,
            metrics=metrics,
            task_breakdown=DashboardService._task_breakdown(tasks),
            progress=DashboardService._progress(db, member_ids),
            recent_items=DashboardService._recent_tasks(tasks),
        )

    @staticmethod
    def _build_mentor(db: Session, members: Query[InternshipMember]) -> DashboardRead:
        member_ids = members.with_entities(InternshipMember.id)
        active_members = members.filter(InternshipMember.status.in_(ACTIVE_MEMBER_STATUSES))
        tasks = DashboardService._tasks(db, member_ids)
        metrics = [
            DashboardMetricRead(
                key="assigned_interns", label="Intern phụ trách", value=active_members.count()
            ),
            DashboardMetricRead(key="cohort_tasks", label="Task của Intern", value=tasks.count()),
            DashboardMetricRead(
                key="pending_reviews",
                label="Bài nộp chờ review",
                value=tasks.filter(Task.status == "SUBMITTED").count(),
            ),
            DashboardMetricRead(
                key="draft_evaluations",
                label="Đánh giá cần hoàn tất",
                value=db.query(Evaluation)
                .filter(
                    Evaluation.internship_member_id.in_(member_ids), Evaluation.status == "DRAFT"
                )
                .count(),
            ),
        ]
        return DashboardRead(
            role=UserRole.MENTOR,
            metrics=metrics,
            task_breakdown=DashboardService._task_breakdown(tasks),
            progress=DashboardService._progress(db, member_ids),
            recent_items=DashboardService._recent_tasks(tasks),
        )

    @staticmethod
    def _build_intern(db: Session, members: Query[InternshipMember]) -> DashboardRead:
        member_ids = members.with_entities(InternshipMember.id)
        active_members = members.filter(InternshipMember.status.in_(ACTIVE_MEMBER_STATUSES))
        tasks = DashboardService._tasks(db, member_ids)
        latest_score = (
            db.query(Evaluation.total_score)
            .filter(
                Evaluation.internship_member_id.in_(member_ids), Evaluation.status == "PUBLISHED"
            )
            .order_by(Evaluation.published_at.desc())
            .first()
        )
        metrics = [
            DashboardMetricRead(
                key="active_memberships",
                label="Đợt thực tập đang tham gia",
                value=active_members.count(),
            ),
            DashboardMetricRead(key="assigned_tasks", label="Task được giao", value=tasks.count()),
            DashboardMetricRead(
                key="in_progress_tasks",
                label="Task đang thực hiện",
                value=tasks.filter(Task.status == "IN_PROGRESS").count(),
            ),
            DashboardMetricRead(
                key="tasks_needing_action",
                label="Task cần xử lý",
                value=tasks.filter(Task.status.in_(("SUBMITTED", "REVISION_REQUIRED"))).count(),
            ),
            DashboardMetricRead(
                key="completed_quizzes",
                label="Quiz đã hoàn thành",
                value=db.query(QuizAttempt)
                .filter(
                    QuizAttempt.internship_member_id.in_(member_ids),
                    QuizAttempt.submitted_at.is_not(None),
                )
                .count(),
            ),
            DashboardMetricRead(
                key="latest_evaluation_score",
                label="Điểm đánh giá gần nhất",
                value=round(float(latest_score[0]), 2)
                if latest_score and latest_score[0] is not None
                else "—",
            ),
        ]
        return DashboardRead(
            role=UserRole.INTERN,
            metrics=metrics,
            task_breakdown=DashboardService._task_breakdown(tasks),
            progress=DashboardService._progress(db, member_ids),
            recent_items=DashboardService._recent_tasks(tasks),
        )

    @staticmethod
    def _active_user_count(members: Query[InternshipMember], user_column) -> int:
        return (
            members.join(User, User.id == user_column)
            .filter(User.status == UserStatus.ACTIVE, user_column.is_not(None))
            .with_entities(func.count(func.distinct(user_column)))
            .scalar()
            or 0
        )

    @staticmethod
    def _tasks(db: Session, member_ids) -> Query[Task]:
        return db.query(Task).filter(Task.internship_member_id.in_(member_ids))

    @staticmethod
    def _task_breakdown(tasks: Query[Task]) -> DashboardTaskBreakdownRead:
        statuses = ("TODO", "IN_PROGRESS", "SUBMITTED", "REVISION_REQUIRED", "COMPLETED")
        counts = {status: 0 for status in statuses}
        for status, count in tasks.with_entities(Task.status, func.count(Task.id)).group_by(
            Task.status
        ):
            if status in counts:
                counts[status] = count
        overdue = tasks.filter(
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.deadline.is_not(None),
            Task.deadline < datetime.now(UTC),
        ).count()
        return DashboardTaskBreakdownRead(
            todo=counts["TODO"],
            in_progress=counts["IN_PROGRESS"],
            submitted=counts["SUBMITTED"],
            revision_required=counts["REVISION_REQUIRED"],
            completed=counts["COMPLETED"],
            overdue=overdue,
        )

    @staticmethod
    def _progress(db: Session, member_ids) -> DashboardProgressRead | None:
        progress = db.query(LearningProgress).filter(
            LearningProgress.internship_member_id.in_(member_ids)
        )
        total = progress.count()
        if total == 0:
            return None
        completed = progress.filter(LearningProgress.status == "COMPLETED").count()
        return DashboardProgressRead(
            percent=round(completed / total * 100, 2),
            completed=completed,
            total=total,
        )

    @staticmethod
    def _recent_tasks(tasks: Query[Task]) -> list[DashboardRecentItemRead]:
        rows = (
            tasks.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc()).limit(5).all()
        )
        return [
            DashboardRecentItemRead(
                title=task.title,
                subtitle=f"Ưu tiên: {task.priority}" if task.priority else None,
                status=task.status,
                due_at=task.deadline,
            )
            for task in rows
        ]
