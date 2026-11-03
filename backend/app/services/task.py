from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import UserRole
from app.models.internship import Internship, InternshipMember
from app.models.task import Task, TaskAssignee, TaskComment, TaskSubmission
from app.models.user import User
from app.schemas.task import (
    SubmissionCreate,
    TaskCommentCreate,
    TaskCreate,
    TaskReviewPayload,
    TaskUpdate,
)


def _is_mentor(user: User) -> bool:
    return str(user.role) == UserRole.MENTOR or user.role == "MENTOR"


def _is_intern(user: User) -> bool:
    return str(user.role) == UserRole.INTERN or user.role == "INTERN"


class TaskService:
    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _get_member(db: Session, member_id: uuid.UUID) -> InternshipMember:
        member = db.query(InternshipMember).filter(InternshipMember.id == member_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Internship member not found"
            )
        return member

    @staticmethod
    def _get_task(db: Session, task_id: uuid.UUID, *, lock: bool = False) -> Task:
        query = db.query(Task).filter(Task.id == task_id)
        if lock:
            query = query.with_for_update()
        task = query.first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    @staticmethod
    def _assert_member_access(user: User, member: InternshipMember) -> None:
        # UC-7: Admin không tham gia quản lý Task -> rơi xuống 403.
        if _is_mentor(user):
            if member.mentor_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Intern is not assigned to this mentor",
                )
            return
        if _is_intern(user):
            if member.intern_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Task is not assigned to this intern",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role not allowed for tasks"
        )

    @classmethod
    def _assert_task_access(cls, db: Session, user: User, task: Task) -> InternshipMember:
        members = cls._task_members(db, task)
        for member in members:
            if (_is_mentor(user) and member.mentor_id == user.id) or (
                _is_intern(user) and member.intern_id == user.id
            ):
                return member
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Task is not assigned to you"
        )

    @staticmethod
    def _task_members(db: Session, task: Task) -> list[InternshipMember]:
        return (
            db.query(InternshipMember)
            .options(joinedload(InternshipMember.intern))
            .join(TaskAssignee, TaskAssignee.internship_member_id == InternshipMember.id)
            .filter(TaskAssignee.task_id == task.id)
            .order_by(InternshipMember.id)
            .all()
        )

    @classmethod
    def _enrich(cls, task: Task, db: Session, user: User | None = None) -> dict:
        members = cls._task_members(db, task)
        internship_names = dict(
            db.query(Internship.id, Internship.name)
            .filter(Internship.id.in_({member.internship_id for member in members}))
            .all()
        )
        assignment_statuses = {a.internship_member_id: a.status for a in task.assignees}
        assignees = [
            {
                "internship_member_id": member.id,
                "intern_id": member.intern_id,
                "intern_name": member.intern.full_name,
                "internship_id": member.internship_id,
                "status": (
                    assignment_statuses[member.id]
                    if task.assignment_mode == "INDIVIDUAL"
                    else task.status
                ),
                "internship_name": internship_names[member.internship_id],
            }
            for member in members
        ]
        submission_query = db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id)
        current_status = task.status
        if task.assignment_mode == "INDIVIDUAL" and user is not None and _is_intern(user):
            own_ids = [m.id for m in members if m.intern_id == user.id]
            submission_query = submission_query.filter(
                TaskSubmission.internship_member_id.in_(own_ids)
            )
            own_assignment = next(
                (a for a in task.assignees if a.internship_member_id in own_ids), None
            )
            if own_assignment:
                current_status = own_assignment.status
        submissions_count = submission_query.count()
        comments_count = (
            db.query(func.count(TaskComment.id)).filter(TaskComment.task_id == task.id).scalar()
            or 0
        )
        now = datetime.now(UTC)
        is_overdue = bool(
            task.deadline is not None
            and current_status in ("TODO", "SUBMITTED", "REVISION_REQUIRED")
            and task.deadline < now
        )
        is_late = bool(
            task.deadline is not None
            and submission_query.filter(TaskSubmission.submitted_at > task.deadline).first()
            is not None
        )
        return {
            "internship_member_id": members[0].id if members else None,
            "internship_member_ids": [member.id for member in members],
            "assignees": assignees,
            "intern_name": ", ".join(a["intern_name"] for a in assignees) or None,
            "internship_name": ", ".join(dict.fromkeys(a["internship_name"] for a in assignees))
            or None,
            "submissions_count": submissions_count,
            "comments_count": comments_count,
            "is_overdue": is_overdue,
            "is_late_submission": is_late,
        }

    @staticmethod
    def _validate_attachment_url(url: str | None) -> str | None:
        if url is None:
            return None
        url = url.strip()
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment URL must not be empty",
            )
        if not (url.startswith("/api/v1/uploads/") or url.startswith("http")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment must reference an uploaded file URL",
            )
        return url

    @staticmethod
    def _submission_to_dict(s: TaskSubmission, deadline: datetime | None, db: Session) -> dict:
        return {
            "id": s.id,
            "task_id": s.task_id,
            "internship_member_id": s.internship_member_id,
            "intern_name": (
                db.get(InternshipMember, s.internship_member_id).intern.full_name
                if s.internship_member_id
                else None
            ),
            "content": s.content,
            "file_url": s.file_url,
            "status": s.status,
            "review_comment": s.review_comment,
            "reviewed_by": s.reviewed_by,
            "submitted_at": s.submitted_at,
            "reviewed_at": s.reviewed_at,
            "is_late": bool(deadline is not None and s.submitted_at > deadline),
        }

    # -- CRUD ------------------------------------------------------------
    @classmethod
    def list_tasks(
        cls,
        db: Session,
        user: User,
        member_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        priority: str | None = None,
        overdue: bool | None = None,
        search: str | None = None,
        internship_id: uuid.UUID | None = None,
    ) -> list[dict]:
        query = db.query(Task)
        if _is_mentor(user):
            allowed = select(InternshipMember.id).where(InternshipMember.mentor_id == user.id)
            query = query.filter(Task.assignees.any(TaskAssignee.internship_member_id.in_(allowed)))
        elif _is_intern(user):
            allowed = select(InternshipMember.id).where(InternshipMember.intern_id == user.id)
            query = query.filter(Task.assignees.any(TaskAssignee.internship_member_id.in_(allowed)))
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not allowed")

        if member_id:
            member = cls._get_member(db, member_id)
            cls._assert_member_access(user, member)
            query = query.filter(Task.assignees.any(TaskAssignee.internship_member_id == member_id))
        if internship_id:
            in_period = select(InternshipMember.id).where(
                InternshipMember.internship_id == internship_id
            )
            query = query.filter(
                Task.assignees.any(TaskAssignee.internship_member_id.in_(in_period))
            )
        if status_filter:
            if _is_intern(user):
                query = query.filter(
                    or_(
                        (Task.assignment_mode == "GROUP") & (Task.status == status_filter),
                        (Task.assignment_mode == "INDIVIDUAL")
                        & Task.assignees.any(
                            (TaskAssignee.internship_member_id.in_(allowed))
                            & (TaskAssignee.status == status_filter)
                        ),
                    )
                )
            else:
                query = query.filter(Task.status == status_filter)
        if priority:
            query = query.filter(Task.priority == priority)
        if search:
            pattern = f"%{search.strip()}%"
            members_matching_name = (
                select(InternshipMember.id)
                .join(User, User.id == InternshipMember.intern_id)
                .where(User.full_name.ilike(pattern))
            )
            query = query.filter(
                or_(
                    Task.title.ilike(pattern),
                    Task.assignees.any(
                        TaskAssignee.internship_member_id.in_(members_matching_name)
                    ),
                )
            )
        tasks = query.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc()).all()

        now = datetime.now(UTC)
        result = []
        for t in tasks:
            enriched = cls._enrich(t, db, user)
            if overdue is True and not enriched["is_overdue"]:
                continue
            if overdue is False and enriched["is_overdue"]:
                continue
            _ = now
            result.append({**_task_to_dict(t), **enriched})
        return result

    @classmethod
    def create_task(cls, db: Session, user: User, data: TaskCreate) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can create tasks"
            )
        members = [cls._get_member(db, member_id) for member_id in data.internship_member_ids]
        for member in members:
            cls._assert_member_access(user, member)
        if len({member.intern_id for member in members}) != len(members):
            raise HTTPException(
                status_code=400, detail="An intern can only be assigned once per task"
            )
        if not data.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Title must not be empty"
            )
        task = Task(
            assignees=[TaskAssignee(internship_member_id=member.id) for member in members],
            assignment_mode=data.assignment_mode,
            created_by=user.id,
            title=data.title.strip(),
            description=data.description,
            deadline=data.deadline,
            priority=data.priority,
            attachment_url=cls._validate_attachment_url(data.attachment_url),
            status="TODO",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {**_task_to_dict(task), **cls._enrich(task, db, user)}

    @classmethod
    def get_detail(cls, db: Session, user: User, task_id: uuid.UUID) -> dict:
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        submission_query = db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id)
        if task.assignment_mode == "INDIVIDUAL" and _is_intern(user):
            member = cls._assert_task_access(db, user, task)
            submission_query = submission_query.filter(
                TaskSubmission.internship_member_id == member.id
            )
        submissions = submission_query.all()
        comments = (
            db.query(TaskComment)
            .filter(TaskComment.task_id == task.id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )
        comment_dicts = []
        for c in comments:
            author = db.query(User).filter(User.id == c.user_id).first()
            comment_dicts.append(
                {
                    "id": c.id,
                    "task_id": c.task_id,
                    "user_id": c.user_id,
                    "author_name": author.full_name if author else None,
                    "author_role": str(author.role) if author else None,
                    "content": c.content,
                    "created_at": c.created_at,
                }
            )
        base = {**_task_to_dict(task), **cls._enrich(task, db, user)}
        base["submissions"] = [cls._submission_to_dict(s, task.deadline, db) for s in submissions]
        base["comments"] = comment_dicts
        return base

    @classmethod
    def update_task(cls, db: Session, user: User, task_id: uuid.UUID, data: TaskUpdate) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can edit tasks"
            )
        task = cls._get_task(db, task_id, lock=True)
        cls._assert_task_access(db, user, task)
        if task.status in ("COMPLETED", "CANCELLED"):
            patch = data.model_dump(exclude_unset=True)
            # Cho phép mentor mở lại task đã hoàn thành/hủy (đổi status), nhưng không sửa nội dung
            non_status = {k for k in patch if k != "status"}
            if non_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Completed/Cancelled task cannot be edited; reopen via status change",
                )
        update = data.model_dump(exclude_unset=True)
        if "attachment_url" in update:
            update["attachment_url"] = cls._validate_attachment_url(update["attachment_url"])
        if "title" in update and update["title"] is not None:
            update["title"] = update["title"].strip()
            if not update["title"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Title must not be empty"
                )
        for field, value in update.items():
            setattr(task, field, value)
        if "status" in update:
            for assignment in task.assignees:
                assignment.status = task.status
        task.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
        return {**_task_to_dict(task), **cls._enrich(task, db, user)}

    @classmethod
    def cancel_task(cls, db: Session, user: User, task_id: uuid.UUID) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can cancel tasks"
            )
        task = cls._get_task(db, task_id, lock=True)
        cls._assert_task_access(db, user, task)
        task.status = "CANCELLED"
        for assignment in task.assignees:
            assignment.status = "CANCELLED"
        task.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
        return {**_task_to_dict(task), **cls._enrich(task, db, user)}

    # -- submission / review ---------------------------------------------
    @staticmethod
    def _refresh_status(task: Task) -> None:
        statuses = [assignment.status for assignment in task.assignees]
        if statuses and all(value == "COMPLETED" for value in statuses):
            task.status = "COMPLETED"
        elif "SUBMITTED" in statuses:
            task.status = "SUBMITTED"
        elif "REVISION_REQUIRED" in statuses:
            task.status = "REVISION_REQUIRED"
        else:
            task.status = "TODO"

    @classmethod
    def submit_task(
        cls, db: Session, user: User, task_id: uuid.UUID, data: SubmissionCreate
    ) -> dict:
        if not _is_intern(user):
            raise HTTPException(status_code=403, detail="Only Intern can submit tasks")
        task = cls._get_task(db, task_id, lock=True)
        member = cls._assert_task_access(db, user, task)
        assignment = next(a for a in task.assignees if a.internship_member_id == member.id)
        if task.status in ("COMPLETED", "CANCELLED") or (
            task.assignment_mode == "INDIVIDUAL" and assignment.status == "COMPLETED"
        ):
            raise HTTPException(
                status_code=400, detail="Task is already closed and cannot receive submissions"
            )
        content = (data.content or "").strip()
        link = (data.link or "").strip()
        file_url = (data.file_url or "").strip()
        if not content and not link and not file_url:
            raise HTTPException(
                status_code=400,
                detail="Submission requires at least one of content, link, attachment_url",
            )
        member_id = member.id if task.assignment_mode == "INDIVIDUAL" else None
        submission = (
            db.query(TaskSubmission)
            .filter(
                TaskSubmission.task_id == task.id,
                TaskSubmission.internship_member_id == member_id,
            )
            .first()
        )
        now = datetime.now(UTC)
        if submission is None:
            submission = TaskSubmission(task_id=task.id, internship_member_id=member_id)
            db.add(submission)
        submission.content = content or link or None
        submission.file_url = file_url or link or None
        submission.status = "SUBMITTED"
        submission.review_comment = None
        submission.reviewed_by = None
        submission.reviewed_at = None
        submission.submitted_at = now
        if task.assignment_mode == "INDIVIDUAL":
            assignment.status = "SUBMITTED"
            cls._refresh_status(task)
        else:
            task.status = "SUBMITTED"
            for assignee in task.assignees:
                assignee.status = task.status
        task.updated_at = now
        db.commit()
        db.refresh(submission)
        return cls._submission_to_dict(submission, task.deadline, db)

    @classmethod
    def delete_submission(cls, db: Session, user: User, task_id: uuid.UUID) -> None:
        if not _is_intern(user):
            raise HTTPException(status_code=403, detail="Only Intern can delete submissions")
        task = cls._get_task(db, task_id, lock=True)
        member = cls._assert_task_access(db, user, task)
        assignment = next(a for a in task.assignees if a.internship_member_id == member.id)
        if task.status in ("COMPLETED", "CANCELLED") or (
            task.assignment_mode == "INDIVIDUAL" and assignment.status == "COMPLETED"
        ):
            raise HTTPException(
                status_code=400,
                detail="Task is already closed and its submission cannot be deleted",
            )
        member_id = member.id if task.assignment_mode == "INDIVIDUAL" else None
        submission = (
            db.query(TaskSubmission)
            .filter(
                TaskSubmission.task_id == task.id,
                TaskSubmission.internship_member_id == member_id,
            )
            .first()
        )
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        db.delete(submission)
        if task.assignment_mode == "INDIVIDUAL":
            assignment.status = "TODO"
            cls._refresh_status(task)
        else:
            task.status = "TODO"
            for assignee in task.assignees:
                assignee.status = task.status
        task.updated_at = datetime.now(UTC)
        db.commit()

    @classmethod
    def review_task(
        cls, db: Session, user: User, task_id: uuid.UUID, payload: TaskReviewPayload
    ) -> dict:
        if not _is_mentor(user):
            raise HTTPException(status_code=403, detail="Only Mentor can review tasks")
        task = cls._get_task(db, task_id, lock=True)
        cls._assert_task_access(db, user, task)
        if task.status == "CANCELLED":
            raise HTTPException(status_code=400, detail="Cancelled task cannot be reviewed")
        assignment = None
        member_id = None
        if task.assignment_mode == "INDIVIDUAL":
            if payload.internship_member_id is None:
                raise HTTPException(
                    status_code=422, detail="Choose the intern whose submission to review"
                )
            assignment = next(
                (
                    a
                    for a in task.assignees
                    if a.internship_member_id == payload.internship_member_id
                ),
                None,
            )
            if assignment is None:
                raise HTTPException(status_code=400, detail="Intern is not assigned to this task")
            cls._assert_member_access(user, cls._get_member(db, payload.internship_member_id))
            member_id = payload.internship_member_id
        latest = (
            db.query(TaskSubmission)
            .filter(
                TaskSubmission.task_id == task.id,
                TaskSubmission.internship_member_id == member_id,
            )
            .first()
        )
        if latest is None:
            raise HTTPException(status_code=400, detail="No submission to review yet")
        now = datetime.now(UTC)
        latest.status = "ACCEPTED" if payload.decision == "COMPLETED" else "REVISION_REQUIRED"
        latest.review_comment = payload.review_comment
        latest.reviewed_by = user.id
        latest.reviewed_at = now
        if assignment is not None:
            assignment.status = payload.decision
            cls._refresh_status(task)
        else:
            task.status = payload.decision
            for assignee in task.assignees:
                assignee.status = task.status
        task.updated_at = now
        db.commit()
        db.refresh(latest)
        return cls._submission_to_dict(latest, task.deadline, db)

    # -- comments (FR-20) -------------------------------------------------
    @classmethod
    def list_comments(cls, db: Session, user: User, task_id: uuid.UUID) -> list[dict]:
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        comments = (
            db.query(TaskComment)
            .filter(TaskComment.task_id == task.id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )
        result = []
        for c in comments:
            author = db.query(User).filter(User.id == c.user_id).first()
            result.append(
                {
                    "id": c.id,
                    "task_id": c.task_id,
                    "user_id": c.user_id,
                    "author_name": author.full_name if author else None,
                    "author_role": str(author.role) if author else None,
                    "content": c.content,
                    "created_at": c.created_at,
                }
            )
        return result

    @classmethod
    def add_comment(
        cls, db: Session, user: User, task_id: uuid.UUID, data: TaskCommentCreate
    ) -> dict:
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        text = data.content.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Comment must not be empty"
            )
        comment = TaskComment(task_id=task.id, user_id=user.id, content=text)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return {
            "id": comment.id,
            "task_id": comment.task_id,
            "user_id": comment.user_id,
            "author_name": user.full_name,
            "author_role": str(user.role),
            "content": comment.content,
            "created_at": comment.created_at,
        }


def _task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "created_by": t.created_by,
        "title": t.title,
        "assignment_mode": t.assignment_mode,
        "description": t.description,
        "deadline": t.deadline,
        "priority": t.priority,
        "attachment_url": t.attachment_url,
        "status": t.status,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
