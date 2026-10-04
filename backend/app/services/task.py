from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.internship import Internship, InternshipMember
from app.models.task import Task, TaskComment, TaskSubmission
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
    def _get_task(db: Session, task_id: uuid.UUID) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
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
        member = cls._get_member(db, task.internship_member_id)
        cls._assert_member_access(user, member)
        return member

    @staticmethod
    def _enrich(task: Task, db: Session) -> dict:
        member = (
            db.query(InternshipMember)
            .filter(InternshipMember.id == task.internship_member_id)
            .first()
        )
        intern_name = None
        internship_name = None
        if member is not None and member.intern is not None:
            intern_name = member.intern.full_name
        if member is not None:
            internship_name = (
                db.query(Internship.name)
                .filter(Internship.id == member.internship_id)
                .scalar()
            )
        submissions_count = (
            db.query(func.count(TaskSubmission.id))
            .filter(TaskSubmission.task_id == task.id)
            .scalar()
            or 0
        )
        comments_count = (
            db.query(func.count(TaskComment.id)).filter(TaskComment.task_id == task.id).scalar()
            or 0
        )
        now = datetime.now(UTC)
        is_overdue = bool(
            task.deadline is not None
            and task.status in ("TODO", "SUBMITTED", "REVISION_REQUIRED")
            and task.deadline < now
        )
        latest = (
            db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).first()
        )
        is_late = bool(
            latest is not None and task.deadline is not None and latest.submitted_at > task.deadline
        )
        return {
            "intern_name": intern_name,
            "internship_name": internship_name,
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
    def _submission_to_dict(s: TaskSubmission, deadline: datetime | None) -> dict:
        return {
            "id": s.id,
            "task_id": s.task_id,
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
            query = query.filter(Task.internship_member_id.in_(allowed))
        elif _is_intern(user):
            allowed = select(InternshipMember.id).where(InternshipMember.intern_id == user.id)
            query = query.filter(Task.internship_member_id.in_(allowed))
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not allowed")

        if member_id:
            member = cls._get_member(db, member_id)
            cls._assert_member_access(user, member)
            query = query.filter(Task.internship_member_id == member_id)
        if internship_id:
            in_period = select(InternshipMember.id).where(
                InternshipMember.internship_id == internship_id
            )
            query = query.filter(Task.internship_member_id.in_(in_period))
        if status_filter:
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
                    Task.internship_member_id.in_(members_matching_name),
                )
            )
        tasks = query.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc()).all()

        now = datetime.now(UTC)
        result = []
        for t in tasks:
            enriched = cls._enrich(t, db)
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
        member = cls._get_member(db, data.internship_member_id)
        cls._assert_member_access(user, member)
        task = Task(
            internship_member_id=member.id,
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
        return {**_task_to_dict(task), **cls._enrich(task, db)}

    @classmethod
    def get_detail(cls, db: Session, user: User, task_id: uuid.UUID) -> dict:
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        submissions = (
            db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).all()
        )
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
        base = {**_task_to_dict(task), **cls._enrich(task, db)}
        base["submissions"] = [cls._submission_to_dict(s, task.deadline) for s in submissions]
        base["comments"] = comment_dicts
        return base

    @classmethod
    def update_task(cls, db: Session, user: User, task_id: uuid.UUID, data: TaskUpdate) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can edit tasks"
            )
        task = cls._get_task(db, task_id)
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
        task.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
        return {**_task_to_dict(task), **cls._enrich(task, db)}

    @classmethod
    def cancel_task(cls, db: Session, user: User, task_id: uuid.UUID) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can cancel tasks"
            )
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        task.status = "CANCELLED"
        task.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
        return {**_task_to_dict(task), **cls._enrich(task, db)}

    # -- submission / review (FR-18, FR-19, BR-03) -----------------------
    @classmethod
    def submit_task(
        cls, db: Session, user: User, task_id: uuid.UUID, data: SubmissionCreate
    ) -> dict:
        if not _is_intern(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Intern can submit tasks"
            )
        task = cls._get_task(db, task_id)
        member = cls._assert_task_access(db, user, task)
        if member.intern_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your task")
        if task.status in ("COMPLETED", "CANCELLED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already closed and cannot receive submissions",
            )
        content = (data.content or "").strip() if data.content else ""
        link = (data.link or "").strip() if data.link else ""
        file_url = data.file_url.strip() if data.file_url else ""
        if not content and not link and not file_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submission requires at least one of content, link, attachment_url",
            )
        now = datetime.now(UTC)
        resolved_content = content or (link if link and not content else None)
        resolved_file = file_url or link or None
        submission = (
            db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).first()
        )
        if submission is None:
            # Lần nộp đầu: tạo bài nộp duy nhất của task
            submission = TaskSubmission(
                task_id=task.id,
                content=resolved_content,
                file_url=resolved_file,
                status="SUBMITTED",
                submitted_at=now,
            )
            db.add(submission)
        else:
            # Nộp lại: ghi đè bài nộp hiện tại, mở lại vòng review
            submission.content = resolved_content
            submission.file_url = resolved_file
            submission.status = "SUBMITTED"
            submission.review_comment = None
            submission.reviewed_by = None
            submission.reviewed_at = None
            submission.submitted_at = now
        task.status = "SUBMITTED"
        task.updated_at = now
        db.commit()
        db.refresh(submission)
        db.refresh(task)
        return cls._submission_to_dict(submission, task.deadline)

    @classmethod
    def delete_submission(
        cls, db: Session, user: User, task_id: uuid.UUID
    ) -> None:
        if not _is_intern(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Intern can delete submissions",
            )
        task = cls._get_task(db, task_id)
        member = cls._assert_task_access(db, user, task)
        if member.intern_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your task")
        if task.status in ("COMPLETED", "CANCELLED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already closed and its submission cannot be deleted",
            )
        submission = (
            db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).first()
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )
        db.delete(submission)
        task.status = "TODO"
        task.updated_at = datetime.now(UTC)
        db.commit()

    @classmethod
    def review_task(
        cls, db: Session, user: User, task_id: uuid.UUID, payload: TaskReviewPayload
    ) -> dict:
        if not _is_mentor(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Mentor can review tasks"
            )
        task = cls._get_task(db, task_id)
        cls._assert_task_access(db, user, task)
        latest = (
            db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).first()
        )
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No submission to review yet"
            )
        now = datetime.now(UTC)
        if payload.decision == "COMPLETED":
            # BR-03: chỉ Mentor xác nhận hoàn thành
            latest.status = "ACCEPTED"
            latest.review_comment = payload.review_comment
            latest.reviewed_by = user.id
            latest.reviewed_at = now
            task.status = "COMPLETED"
        else:
            latest.status = "REVISION_REQUIRED"
            latest.review_comment = payload.review_comment
            latest.reviewed_by = user.id
            latest.reviewed_at = now
            task.status = "REVISION_REQUIRED"
        task.updated_at = now
        db.commit()
        db.refresh(latest)
        return cls._submission_to_dict(latest, task.deadline)

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
        "internship_member_id": t.internship_member_id,
        "created_by": t.created_by,
        "title": t.title,
        "description": t.description,
        "deadline": t.deadline,
        "priority": t.priority,
        "attachment_url": t.attachment_url,
        "status": t.status,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
