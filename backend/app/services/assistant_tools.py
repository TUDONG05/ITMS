from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.enums import InternshipMemberStatus, UserRole, UserStatus
from app.models.evaluation import Evaluation
from app.models.exam import Quiz, QuizAttempt
from app.models.internship import Internship, InternshipMember
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.task import Task
from app.models.user import User
from app.services.notification import NotificationService

MAX_TOOL_ROWS = 20
MAX_TOOL_TEXT_CHARS = 2000
TASK_STATUSES = ("TODO", "SUBMITTED", "REVISION_REQUIRED", "COMPLETED", "CANCELLED")
ACTIVE_MEMBER_STATUSES = (InternshipMemberStatus.ACTIVE, InternshipMemberStatus.EXTENDED)


def _uuid(value: Any, field_name: str = "intern_id") -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise ApiError(
            422,
            "INVALID_TOOL_ARGUMENT",
            f"{field_name} không hợp lệ.",
        ) from None


def _limit(value: Any, default: int = 10) -> int:
    try:
        parsed = int(value if value is not None else default)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, MAX_TOOL_ROWS))


class AuthorizedScopeService:
    @staticmethod
    def lock_scope(db: Session, user: User) -> None:
        db.execute(select(User.id).where(User.id == user.id).with_for_update()).one_or_none()
        if user.role == UserRole.ADMIN:
            return
        predicate = (
            InternshipMember.intern_id == user.id
            if user.role == UserRole.INTERN
            else InternshipMember.mentor_id == user.id
        )
        db.execute(select(InternshipMember.id).where(predicate).with_for_update()).all()

    @staticmethod
    def assert_current_user(db: Session, user: User) -> None:
        current = db.execute(select(User.role, User.status).where(User.id == user.id)).one_or_none()
        if (
            current is None
            or current.role != user.role
            or current.status != user.status
            or current.status != UserStatus.ACTIVE
        ):
            raise ApiError(
                409,
                "AI_SCOPE_CHANGED",
                "Quyền truy cập đã thay đổi trong lúc xử lý. Vui lòng hỏi lại.",
            )

    @staticmethod
    def member_query(user: User, intern_id: uuid.UUID | None = None):
        query = select(InternshipMember)
        if user.role == UserRole.INTERN:
            return query.where(InternshipMember.intern_id == user.id)
        if user.role == UserRole.MENTOR:
            query = query.where(InternshipMember.mentor_id == user.id)
        elif user.role != UserRole.ADMIN:
            raise ApiError(403, "FORBIDDEN", "Bạn không có quyền sử dụng trợ lý AI.")
        if intern_id is not None:
            query = query.where(InternshipMember.intern_id == intern_id)
        return query

    @classmethod
    def members(
        cls, db: Session, user: User, intern_id: uuid.UUID | None = None
    ) -> list[InternshipMember]:
        rows = list(
            db.scalars(
                cls.member_query(user, intern_id).order_by(
                    InternshipMember.updated_at.desc(), InternshipMember.created_at.desc()
                )
            )
        )
        if intern_id is not None and not rows and user.role != UserRole.INTERN:
            raise ApiError(404, "INTERN_NOT_FOUND", "Không tìm thấy thực tập sinh trong phạm vi.")
        return rows

    @staticmethod
    def fingerprint(db: Session, user: User) -> tuple[Any, ...]:
        current = db.execute(select(User.role, User.status).where(User.id == user.id)).one_or_none()
        if current is None:
            return ("MISSING",)
        if current.role == UserRole.ADMIN:
            return (current.role, current.status)
        if current.role == UserRole.INTERN:
            predicate = InternshipMember.intern_id == user.id
        elif current.role == UserRole.MENTOR:
            predicate = InternshipMember.mentor_id == user.id
        else:
            return (current.role, current.status, "UNSUPPORTED")
        memberships = db.execute(
            select(
                InternshipMember.id,
                InternshipMember.intern_id,
                InternshipMember.mentor_id,
                InternshipMember.roadmap_id,
                InternshipMember.status,
            ).where(predicate)
        ).all()
        return (current.role, current.status, tuple(sorted(map(str, memberships))))


class AssistantToolService:
    def execute(self, db: Session, user: User, name: str, arguments: dict[str, Any]) -> dict:
        handlers = {
            "get_mentor_assignment": self.get_mentor_assignment,
            "find_accessible_interns": self.find_accessible_interns,
            "get_roadmap": self.get_roadmap,
            "get_learning_progress": self.get_learning_progress,
            "get_tasks": self.get_tasks,
            "get_deadlines": self.get_deadlines,
            "get_quiz_results": self.get_quiz_results,
            "get_evaluations": self.get_evaluations,
            "get_notifications": self.get_notifications,
        }
        handler = handlers.get(name)
        if handler is None:
            raise ApiError(422, "UNKNOWN_AI_TOOL", "Trợ lý yêu cầu một công cụ không hợp lệ.")
        return handler(db, user, arguments)

    @staticmethod
    def _member_ids(db: Session, user: User, arguments: dict[str, Any]) -> list[uuid.UUID]:
        intern_id = None if user.role == UserRole.INTERN else _uuid(arguments.get("intern_id"))
        return [member.id for member in AuthorizedScopeService.members(db, user, intern_id)]

    def find_accessible_interns(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        query_text = str(arguments.get("query") or "").strip()
        limit = _limit(arguments.get("limit"), 5)
        query = (
            select(User, InternshipMember, Internship)
            .join(InternshipMember, InternshipMember.intern_id == User.id)
            .join(Internship, Internship.id == InternshipMember.internship_id)
            .where(User.role == UserRole.INTERN)
        )
        if user.role == UserRole.INTERN:
            query = query.where(User.id == user.id)
        elif user.role == UserRole.MENTOR:
            query = query.where(InternshipMember.mentor_id == user.id)
        elif user.role != UserRole.ADMIN:
            raise ApiError(403, "FORBIDDEN", "Bạn không có quyền sử dụng trợ lý AI.")
        if query_text:
            pattern = f"%{query_text}%"
            query = query.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
        total_count = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        rows = db.execute(query.order_by(User.full_name).limit(limit)).all()
        return {
            "total_count": total_count,
            "returned_count": len(rows),
            "truncated": len(rows) < total_count,
            "interns": [
                {
                    "intern_id": str(intern.id),
                    "full_name": intern.full_name,
                    "internship": internship.name,
                    "member_status": member.status,
                }
                for intern, member, internship in rows
            ],
        }

    def get_notifications(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        status = str(arguments.get("status") or "ALL").upper()
        if status not in ("ALL", "UNREAD"):
            raise ApiError(422, "INVALID_TOOL_ARGUMENT", "Trạng thái thông báo không hợp lệ.")

        if user.role == UserRole.ADMIN:
            if status == "UNREAD":
                raise ApiError(
                    422,
                    "INVALID_TOOL_ARGUMENT",
                    "Quản trị viên không có trạng thái đã đọc hoặc chưa đọc cho thông báo đã gửi.",
                )
            rows = NotificationService.list_notifications_admin(db, user)
            scope = "ALL_SENT"
            unread_count = None
        elif user.role in (UserRole.MENTOR, UserRole.INTERN):
            rows = NotificationService.list_notifications_user(db, user)
            scope = "RECEIVED"
            unread_count = 0
        else:
            raise ApiError(403, "FORBIDDEN", "Bạn không có quyền sử dụng trợ lý AI.")

        query_text = str(arguments.get("query") or "").strip().casefold()
        if query_text:
            rows = [
                item
                for item in rows
                if query_text in str(item["title"]).casefold()
                or query_text in str(item["content"]).casefold()
            ]

        if user.role in (UserRole.MENTOR, UserRole.INTERN):
            unread_count = sum(not bool(item["is_read"]) for item in rows)
            if status == "UNREAD":
                rows = [item for item in rows if not item["is_read"]]

        total_count = len(rows)
        limited_rows = rows[: _limit(arguments.get("limit"))]
        notifications = []
        for item in limited_rows:
            notification = {
                "id": str(item["id"]),
                "title": item["title"],
                "content": _bounded_text(item["content"]),
                "target_type": item["target_type"],
                "created_at": item["created_at"],
                "creator_name": item["creator_name"],
            }
            if user.role == UserRole.ADMIN:
                notification.update(
                    {
                        "recipient_names": item["recipient_names"],
                        "read_count": item["read_count"],
                    }
                )
            else:
                notification.update(
                    {
                        "is_read": item["is_read"],
                        "read_at": item["read_at"],
                    }
                )
            notifications.append(notification)

        return {
            "scope": scope,
            "status": status,
            "total_count": total_count,
            "unread_count": unread_count,
            "returned_count": len(notifications),
            "truncated": len(notifications) < total_count,
            "notifications": notifications,
        }

    def get_mentor_assignment(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        intern_id = None if user.role == UserRole.INTERN else _uuid(arguments.get("intern_id"))
        members = AuthorizedScopeService.members(db, user, intern_id)
        limit = _limit(arguments.get("limit"), 10)
        assignments: list[dict[str, Any]] = []

        for member in members:
            if member.status not in ACTIVE_MEMBER_STATUSES:
                continue
            intern = db.get(User, member.intern_id)
            internship = db.get(Internship, member.internship_id)
            mentor = db.get(User, member.mentor_id) if member.mentor_id is not None else None
            if intern is None or internship is None:
                continue
            assignments.append(
                {
                    "intern_id": str(intern.id),
                    "intern_name": intern.full_name,
                    "mentor_id": str(mentor.id) if mentor is not None else None,
                    "mentor_name": mentor.full_name if mentor is not None else None,
                    "internship": internship.name,
                    "member_status": member.status,
                }
            )
            if len(assignments) >= limit:
                break

        return {"assignments": assignments}

    def get_tasks(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        member_ids = self._member_ids(db, user, arguments)
        if not member_ids:
            return {"tasks": [], "total_count": 0, "returned_count": 0, "truncated": False}
        query = (
            select(Task, InternshipMember.intern_id, User.full_name)
            .join(InternshipMember, InternshipMember.id == Task.internship_member_id)
            .join(User, User.id == InternshipMember.intern_id)
            .where(Task.internship_member_id.in_(member_ids))
        )
        status = str(arguments.get("status") or "").upper()
        if status:
            if status not in TASK_STATUSES:
                raise ApiError(422, "INVALID_TOOL_ARGUMENT", "status task không hợp lệ.")
            query = query.where(Task.status == status)
        total_count = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        tasks = db.execute(
            query.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc()).limit(
                _limit(arguments.get("limit"))
            )
        ).all()
        return {
            "total_count": total_count,
            "returned_count": len(tasks),
            "truncated": len(tasks) < total_count,
            "tasks": [
                {
                    "id": str(task.id),
                    "intern_id": str(intern_id),
                    "intern_name": intern_name,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "deadline": task.deadline,
                }
                for task, intern_id, intern_name in tasks
            ],
        }

    def get_deadlines(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        member_ids = self._member_ids(db, user, arguments)
        if not member_ids:
            return {
                "range": str(arguments.get("range") or "NEXT_7_DAYS").upper(),
                "deadlines": [],
                "total_count": 0,
                "returned_count": 0,
                "truncated": False,
            }
        now = datetime.now(UTC)
        range_name = str(arguments.get("range") or "NEXT_7_DAYS").upper()
        query = (
            select(Task, InternshipMember.intern_id, User.full_name)
            .join(InternshipMember, InternshipMember.id == Task.internship_member_id)
            .join(User, User.id == InternshipMember.intern_id)
            .where(
                Task.internship_member_id.in_(member_ids),
                Task.deadline.is_not(None),
                Task.status.not_in(("COMPLETED", "CANCELLED")),
            )
        )
        if range_name == "OVERDUE":
            query = query.where(Task.deadline < now)
        elif range_name == "NEXT_30_DAYS":
            query = query.where(
                and_(Task.deadline >= now, Task.deadline <= now + timedelta(days=30))
            )
        elif range_name == "NEXT":
            query = query.where(Task.deadline >= now)
        else:
            range_name = "NEXT_7_DAYS"
            query = query.where(
                and_(Task.deadline >= now, Task.deadline <= now + timedelta(days=7))
            )
        total_count = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        tasks = db.execute(
            query.order_by(Task.deadline.asc()).limit(_limit(arguments.get("limit")))
        ).all()
        return {
            "range": range_name,
            "total_count": total_count,
            "returned_count": len(tasks),
            "truncated": len(tasks) < total_count,
            "deadlines": [
                {
                    "task_id": str(task.id),
                    "intern_id": str(intern_id),
                    "intern_name": intern_name,
                    "title": task.title,
                    "deadline": task.deadline,
                    "status": task.status,
                    "deadline_state": "OVERDUE"
                    if task.deadline and task.deadline < now
                    else "UPCOMING",
                }
                for task, intern_id, intern_name in tasks
            ],
        }

    def get_roadmap(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        members = AuthorizedScopeService.members(
            db,
            user,
            None if user.role == UserRole.INTERN else _uuid(arguments.get("intern_id")),
        )
        include_contents = bool(arguments.get("include_contents", True))
        roadmaps: list[dict[str, Any]] = []
        for member in members[:MAX_TOOL_ROWS]:
            if user.role == UserRole.INTERN and member.status not in ACTIVE_MEMBER_STATUSES:
                continue
            if member.roadmap_id is None:
                continue
            roadmap = db.get(Roadmap, member.roadmap_id)
            if roadmap is None or (user.role == UserRole.INTERN and roadmap.status != "ACTIVE"):
                continue
            phase_rows = list(
                db.scalars(
                    select(Phase)
                    .where(Phase.roadmap_id == roadmap.id)
                    .order_by(Phase.order_no)
                    .limit(MAX_TOOL_ROWS)
                )
            )
            phases = []
            for phase in phase_rows:
                phase_data: dict[str, Any] = {
                    "id": str(phase.id),
                    "name": phase.name,
                    "order_no": phase.order_no,
                }
                if include_contents:
                    contents = list(
                        db.scalars(
                            select(LearningContent)
                            .where(LearningContent.phase_id == phase.id)
                            .order_by(LearningContent.order_no)
                            .limit(MAX_TOOL_ROWS)
                        )
                    )
                    phase_data["contents"] = [
                        {"id": str(item.id), "title": item.title, "type": item.type}
                        for item in contents[:MAX_TOOL_ROWS]
                    ]
                phases.append(phase_data)
            roadmaps.append(
                {
                    "intern_id": str(member.intern_id),
                    "roadmap_id": str(roadmap.id),
                    "name": roadmap.name,
                    "status": roadmap.status,
                    "phases": phases,
                }
            )
        return {"roadmaps": roadmaps}

    def get_learning_progress(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        members = AuthorizedScopeService.members(
            db,
            user,
            None if user.role == UserRole.INTERN else _uuid(arguments.get("intern_id")),
        )
        summaries = []
        for member in members[:MAX_TOOL_ROWS]:
            if user.role == UserRole.INTERN and member.status not in ACTIVE_MEMBER_STATUSES:
                continue
            if member.roadmap_id is None:
                summaries.append({"intern_id": str(member.intern_id), "roadmap_assigned": False})
                continue
            roadmap = db.get(Roadmap, member.roadmap_id)
            if roadmap is None or (user.role == UserRole.INTERN and roadmap.status != "ACTIVE"):
                continue
            content_ids = list(
                db.scalars(
                    select(LearningContent.id)
                    .join(Phase, Phase.id == LearningContent.phase_id)
                    .where(Phase.roadmap_id == member.roadmap_id)
                )
            )
            progress_rows = (
                list(
                    db.scalars(
                        select(LearningProgress).where(
                            LearningProgress.internship_member_id == member.id,
                            LearningProgress.content_id.in_(content_ids),
                        )
                    )
                )
                if content_ids
                else []
            )
            statuses = {row.content_id: row.status for row in progress_rows}
            completed = sum(statuses.get(content_id) == "COMPLETED" for content_id in content_ids)
            in_progress = sum(
                statuses.get(content_id) == "IN_PROGRESS" for content_id in content_ids
            )
            total = len(content_ids)
            percent_sum = sum(float(row.progress_percent or 0) for row in progress_rows)
            summaries.append(
                {
                    "intern_id": str(member.intern_id),
                    "roadmap_assigned": True,
                    "total_contents": total,
                    "completed_contents": completed,
                    "in_progress_contents": in_progress,
                    "not_started_contents": max(total - completed - in_progress, 0),
                    "progress_percent": round(percent_sum / total, 2) if total else 0,
                }
            )
        return {"progress": summaries}

    def get_quiz_results(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        member_ids = self._member_ids(db, user, arguments)
        if not member_ids:
            return {"quiz_results": []}
        query = (
            select(QuizAttempt, Quiz, InternshipMember.intern_id, User.full_name)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .join(InternshipMember, InternshipMember.id == QuizAttempt.internship_member_id)
            .join(User, User.id == InternshipMember.intern_id)
            .where(QuizAttempt.internship_member_id.in_(member_ids))
        )
        quiz_id = _uuid(arguments.get("quiz_id"), "quiz_id")
        if quiz_id is not None:
            query = query.where(Quiz.id == quiz_id)
        rows = db.execute(query.order_by(QuizAttempt.started_at.desc()).limit(MAX_TOOL_ROWS)).all()
        total_count = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        return {
            "total_count": total_count,
            "returned_count": len(rows),
            "truncated": len(rows) < total_count,
            "quiz_results": [
                {
                    "quiz_id": str(quiz.id),
                    "intern_id": str(intern_id),
                    "intern_name": intern_name,
                    "title": quiz.title,
                    "attempt_no": attempt.attempt_no,
                    "score": float(attempt.score) if attempt.score is not None else None,
                    "passed": attempt.passed,
                    "started_at": attempt.started_at,
                    "submitted_at": attempt.submitted_at,
                }
                for attempt, quiz, intern_id, intern_name in rows
            ],
            "correct_answers_included": False,
        }

    def get_evaluations(self, db: Session, user: User, arguments: dict[str, Any]) -> dict:
        member_ids = self._member_ids(db, user, arguments)
        if not member_ids:
            return {"evaluations": []}
        query = (
            select(Evaluation, InternshipMember.intern_id, User.full_name)
            .join(InternshipMember, InternshipMember.id == Evaluation.internship_member_id)
            .join(User, User.id == InternshipMember.intern_id)
            .where(Evaluation.internship_member_id.in_(member_ids))
        )
        if user.role == UserRole.INTERN:
            query = query.where(Evaluation.status == "PUBLISHED")
        elif user.role == UserRole.MENTOR:
            query = query.where(
                or_(Evaluation.status == "PUBLISHED", Evaluation.mentor_id == user.id)
            )
        requested_status = str(arguments.get("status") or "").upper()
        if requested_status:
            query = query.where(Evaluation.status == requested_status)
        rows = db.execute(
            query.order_by(Evaluation.created_at.desc()).limit(_limit(arguments.get("limit")))
        ).all()
        total_count = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        return {
            "total_count": total_count,
            "returned_count": len(rows),
            "truncated": len(rows) < total_count,
            "evaluations": [
                {
                    "id": str(item.id),
                    "intern_id": str(intern_id),
                    "intern_name": intern_name,
                    "type": item.evaluation_type,
                    "status": item.status,
                    "total_score": float(item.total_score)
                    if item.total_score is not None
                    else None,
                    "comment": _bounded_text(item.comment),
                    "published_at": item.published_at,
                }
                for item, intern_id, intern_name in rows
            ],
        }


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "find_accessible_interns",
            "description": "Tìm thực tập sinh trong phạm vi người dùng được phép xem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            },
        },
    },
    *[
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                },
            },
        }
        for name, description, properties in (
            (
                "get_mentor_assignment",
                (
                    "Lấy thông tin mentor đang phụ trách thực tập sinh; "
                    "dùng cho câu hỏi mentor của tôi là ai."
                ),
                {
                    "intern_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            ),
            (
                "get_roadmap",
                "Lấy roadmap của thực tập sinh được phép xem.",
                {"intern_id": {"type": "string"}, "include_contents": {"type": "boolean"}},
            ),
            (
                "get_learning_progress",
                "Lấy tiến độ học tập đã được backend tính toán.",
                {"intern_id": {"type": "string"}},
            ),
            (
                "get_tasks",
                "Lấy task theo phạm vi và trạng thái.",
                {
                    "intern_id": {"type": "string"},
                    "status": {"type": "string", "enum": list(TASK_STATUSES)},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            ),
            (
                "get_deadlines",
                "Lấy deadline sắp tới hoặc quá hạn do backend phân loại.",
                {
                    "intern_id": {"type": "string"},
                    "range": {
                        "type": "string",
                        "enum": ["NEXT", "NEXT_7_DAYS", "NEXT_30_DAYS", "OVERDUE"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            ),
            (
                "get_quiz_results",
                "Lấy kết quả quiz, không bao gồm đáp án đúng.",
                {"intern_id": {"type": "string"}, "quiz_id": {"type": "string"}},
            ),
            (
                "get_evaluations",
                "Lấy đánh giá trong phạm vi được phép xem.",
                {
                    "intern_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["DRAFT", "PUBLISHED"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            ),
            (
                "get_notifications",
                (
                    "Lấy thông báo trong phạm vi được phép xem. Intern và Mentor xem thông báo "
                    "đã nhận cùng số chưa đọc; Admin xem toàn bộ thông báo đã gửi."
                ),
                {
                    "query": {"type": "string"},
                    "status": {"type": "string", "enum": ["ALL", "UNREAD"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            ),
        )
    ],
]


def _bounded_text(value: str | None) -> str | None:
    if value is None or len(value) <= MAX_TOOL_TEXT_CHARS:
        return value
    return value[: MAX_TOOL_TEXT_CHARS - 1] + "…"
