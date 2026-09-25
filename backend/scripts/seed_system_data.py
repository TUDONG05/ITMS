"""Seed a complete, repeatable development dataset for all ITMS business tables.

Run after ``alembic upgrade head`` against a local development database:

    uv run python scripts/seed_system_data.py

The script intentionally resets the passwords of its controlled ``@itms.local``
demo accounts. It only runs when ``ITMS_ENVIRONMENT=development`` and otherwise
updates the same seed records instead of deleting any existing database data.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

# Direct execution makes ``backend/scripts`` the import root. Include ``backend`` so the
# application's absolute imports work with the documented command.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.core.settings import get_settings
from app.db.session import get_session_factory
from app.models import (
    AIConversation,
    AIMessage,
    Evaluation,
    EvaluationCriterion,
    Internship,
    InternshipMember,
    InternshipRequest,
    LearningContent,
    LearningProgress,
    Notification,
    NotificationRead,
    Phase,
    Question,
    Quiz,
    QuizAttempt,
    Roadmap,
    Task,
    TaskComment,
    TaskSubmission,
    User,
)
from app.models.enums import UserRole, UserStatus

SEED_NAMESPACE = uuid.UUID("d36ab751-1ddf-4b38-a18c-3424cedf5e55")
NOW = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
DEMO_USERS = (
    ("admin", "admin@itms.local", "Admin@12345", "Quản trị viên ITMS", UserRole.ADMIN),
    ("mentor_1", "mentor@itms.local", "Mentor@12345", "Lê Minh Hoàng", UserRole.MENTOR),
    ("mentor_2", "mentor2@itms.local", "Mentor2@12345", "Trần Minh Bình", UserRole.MENTOR),
    ("intern_1", "intern@itms.local", "Intern@12345", "Nguyễn Văn An", UserRole.INTERN),
    ("intern_2", "intern2@itms.local", "Intern2@12345", "Trần Thị Bình", UserRole.INTERN),
    ("intern_3", "intern3@itms.local", "Intern3@12345", "Lê Minh Cường", UserRole.INTERN),
    ("intern_4", "intern4@itms.local", "Intern4@12345", "Phạm Thu Hà", UserRole.INTERN),
    ("intern_5", "intern5@itms.local", "Intern5@12345", "Đỗ Quang Huy", UserRole.INTERN),
)


def seed_id(name: str) -> uuid.UUID:
    """Return a stable identifier so seed rows are safe to run repeatedly."""
    return uuid.uuid5(SEED_NAMESPACE, name)


def upsert_by[ModelT](
    db: Session,
    model: type[ModelT],
    identity: dict[str, Any],
    values: dict[str, Any],
) -> ModelT:
    """Create or refresh one seed row identified by its business key."""
    instance = db.scalar(select(model).filter_by(**identity))
    if instance is None:
        attributes = {**identity, **values}
        instance = model(**attributes)  # type: ignore[call-arg]
        db.add(instance)
    else:
        for field, value in values.items():
            setattr(instance, field, value)
    return instance


def upsert_seed[ModelT](
    db: Session, model: type[ModelT], identifier: uuid.UUID, values: dict[str, Any]
) -> ModelT:
    """Create or refresh a seed-owned row through its stable UUID."""
    instance = db.get(model, identifier)
    if instance is None:
        instance = model(id=identifier, **values)  # type: ignore[call-arg]
        db.add(instance)
    else:
        for field, value in values.items():
            setattr(instance, field, value)
    return instance


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for key, email, password, full_name, role in DEMO_USERS:
        users[key] = upsert_by(
            db,
            User,
            {"email": email},
            {
                "password_hash": hash_password(password),
                "full_name": full_name,
                "role": role,
                "status": UserStatus.ACTIVE,
                "phone": None,
                "avatar_url": None,
                "token_version": 0,
                "password_reset_token_hash": None,
                "password_reset_expires_at": None,
                "password_changed_at": NOW,
            },
        )
    db.flush()
    return users


def main() -> None:
    get_settings()
    if os.getenv("ITMS_ENVIRONMENT", "").casefold() != "development":
        raise RuntimeError("Seed system data may only run when ITMS_ENVIRONMENT=development.")

    session_factory = get_session_factory()
    with session_factory.begin() as db:
        users = seed_users(db)
        admin = users["admin"]
        mentor_1 = users["mentor_1"]
        mentor_2 = users["mentor_2"]

        roadmap = upsert_by(
            db,
            Roadmap,
            {"name": "Lộ trình Full-stack 2026"},
            {
                "description": "Lộ trình nền tảng cho thực tập sinh phát triển phần mềm.",
                "status": "ACTIVE",
                "created_by": admin.id,
            },
        )
        internship = upsert_by(
            db,
            Internship,
            {"name": "Đợt thực tập 2026 - Thu"},
            {
                "description": "Đợt thực tập phát triển phần mềm mùa Thu năm 2026.",
                "start_date": date(2026, 8, 3),
                "end_date": date(2026, 11, 30),
                "status": "ONGOING",
                "created_by": admin.id,
            },
        )
        db.flush()

        phase_specs = (
            (
                "foundation",
                "Giai đoạn 1: Kiến thức nền tảng",
                "Git, quy trình và kiến thức nền tảng.",
                1,
            ),
            ("frontend", "Giai đoạn 2: Frontend cơ bản", "Angular và xây dựng giao diện.", 2),
            ("backend", "Giai đoạn 3: Backend cơ bản", "FastAPI, cơ sở dữ liệu và API.", 3),
        )
        phases: dict[str, Phase] = {}
        for key, name, description, order_no in phase_specs:
            phases[key] = upsert_by(
                db,
                Phase,
                {"roadmap_id": roadmap.id, "order_no": order_no},
                {"name": name, "description": description},
            )
        db.flush()

        content_specs = (
            ("git", "foundation", "Quy trình Git và GitHub", "LESSON", 1),
            ("sdlc", "foundation", "Tài liệu quy trình SDLC", "DOCUMENT", 2),
            ("angular", "frontend", "Angular cơ bản", "VIDEO", 1),
            ("ui", "frontend", "Thiết kế giao diện với NG-ZORRO", "LESSON", 2),
            ("fastapi", "backend", "Xây dựng API với FastAPI", "LESSON", 1),
            ("postgresql", "backend", "Thiết kế dữ liệu PostgreSQL", "DOCUMENT", 2),
        )
        contents: dict[str, LearningContent] = {}
        for key, phase_key, title, content_type, order_no in content_specs:
            contents[key] = upsert_by(
                db,
                LearningContent,
                {"phase_id": phases[phase_key].id, "order_no": order_no},
                {
                    "title": title,
                    "description": f"Nội dung đào tạo: {title}.",
                    "type": content_type,
                    "content": f"Tài liệu hướng dẫn cho {title}.",
                    "resource_url": f"https://docs.itms.local/training/{key}",
                },
            )
        db.flush()

        member_specs = (
            ("intern_1", mentor_1, "ACTIVE"),
            ("intern_2", mentor_1, "ACTIVE"),
            ("intern_3", mentor_1, "ACTIVE"),
            ("intern_4", mentor_2, "EXTENDED"),
            ("intern_5", mentor_2, "ACTIVE"),
        )
        members: dict[str, InternshipMember] = {}
        for intern_key, mentor, status in member_specs:
            members[intern_key] = upsert_by(
                db,
                InternshipMember,
                {"internship_id": internship.id, "intern_id": users[intern_key].id},
                {
                    "mentor_id": mentor.id,
                    "roadmap_id": roadmap.id,
                    "start_date": date(2026, 8, 3),
                    "end_date": date(2026, 11, 30),
                    "status": status,
                },
            )
        db.flush()

        progress_by_member = {
            "intern_1": (100, 100, 80, 70, 40, 0),
            "intern_2": (100, 70, 40, 0, 0, 0),
            "intern_3": (100, 100, 100, 80, 60, 30),
            "intern_4": (100, 100, 100, 100, 80, 50),
            "intern_5": (100, 100, 50, 30, 0, 0),
        }
        for intern_key, percentages in progress_by_member.items():
            for content_key, percentage in zip(contents, percentages, strict=True):
                status = (
                    "COMPLETED"
                    if percentage == 100
                    else "IN_PROGRESS"
                    if percentage
                    else "NOT_STARTED"
                )
                upsert_by(
                    db,
                    LearningProgress,
                    {
                        "internship_member_id": members[intern_key].id,
                        "content_id": contents[content_key].id,
                    },
                    {
                        "status": status,
                        "progress_percent": percentage,
                        "completed_at": NOW if percentage == 100 else None,
                    },
                )

        quiz = upsert_seed(
            db,
            Quiz,
            seed_id("quiz:foundation"),
            {
                "phase_id": phases["foundation"].id,
                "title": "Quiz kiến thức nền tảng",
                "description": "Kiểm tra kiến thức Git và quy trình phát triển phần mềm.",
                "duration_minutes": 30,
                "pass_score": 60,
                "max_attempts": 2,
                "status": "PUBLISHED",
            },
        )
        db.flush()
        questions = (
            (
                "git",
                "Lệnh nào tạo nhánh Git mới?",
                ["git branch", "git commit", "git push"],
                "git branch",
            ),
            (
                "pr",
                "Pull request được dùng để làm gì?",
                ["Review mã", "Xóa repository", "Đổi mật khẩu"],
                "Review mã",
            ),
            ("api", "HTTP 200 biểu thị yêu cầu thành công.", [True, False], True),
        )
        for order_no, (key, content, options, correct_answer) in enumerate(questions, start=1):
            upsert_seed(
                db,
                Question,
                seed_id(f"question:{key}"),
                {
                    "quiz_id": quiz.id,
                    "order_no": order_no,
                    "content": content,
                    "type": "TRUE_FALSE" if key == "api" else "SINGLE_CHOICE",
                    "options": options,
                    "correct_answer": correct_answer,
                    "score": 10,
                },
            )

        for intern_key, score in (("intern_1", 90), ("intern_3", 80), ("intern_4", 100)):
            upsert_by(
                db,
                QuizAttempt,
                {
                    "quiz_id": quiz.id,
                    "internship_member_id": members[intern_key].id,
                    "attempt_no": 1,
                },
                {
                    "answers": ["git branch", "Review mã", True],
                    "score": score,
                    "passed": True,
                    "started_at": NOW,
                    "submitted_at": NOW,
                },
            )

        task_specs = (
            ("intern_1", "Tìm hiểu quy trình SDLC", "HIGH", "IN_PROGRESS", 25),
            ("intern_1", "Viết báo cáo phân tích yêu cầu", "MEDIUM", "SUBMITTED", 28),
            ("intern_2", "Thiết kế database mẫu", "HIGH", "REVISION_REQUIRED", 30),
            ("intern_3", "Xây dựng giao diện đăng nhập", "HIGH", "COMPLETED", 20),
            ("intern_4", "Chuẩn bị demo sprint 1", "MEDIUM", "TODO", 27),
            ("intern_5", "Tích hợp API đăng nhập", "HIGH", "IN_PROGRESS", 29),
        )
        tasks: dict[str, Task] = {}
        for intern_key, title, priority, status, deadline_day in task_specs:
            key = f"{intern_key}:{title}"
            tasks[key] = upsert_seed(
                db,
                Task,
                seed_id(f"task:{key}"),
                {
                    "internship_member_id": members[intern_key].id,
                    "title": title,
                    "created_by": members[intern_key].mentor_id,
                    "description": f"Thực hiện công việc: {title}.",
                    "deadline": datetime(2026, 9, deadline_day, 17, 0, tzinfo=UTC),
                    "priority": priority,
                    "status": status,
                },
            )
        db.flush()

        submitted_task = tasks["intern_1:Viết báo cáo phân tích yêu cầu"]
        revision_task = tasks["intern_2:Thiết kế database mẫu"]
        upsert_by(
            db,
            TaskSubmission,
            {"task_id": submitted_task.id, "version": 1},
            {
                "content": "Báo cáo phân tích yêu cầu phiên bản 1.",
                "file_url": "https://files.itms.local/submissions/requirement-analysis-v1.pdf",
                "status": "SUBMITTED",
                "review_comment": None,
                "reviewed_by": None,
                "submitted_at": NOW,
                "reviewed_at": None,
            },
        )
        upsert_by(
            db,
            TaskSubmission,
            {"task_id": revision_task.id, "version": 1},
            {
                "content": "Sơ đồ dữ liệu phiên bản 1.",
                "file_url": "https://files.itms.local/submissions/database-design-v1.pdf",
                "status": "REVISION_REQUIRED",
                "review_comment": "Bổ sung ràng buộc khóa ngoại và mô tả các bảng.",
                "reviewed_by": mentor_1.id,
                "submitted_at": NOW,
                "reviewed_at": NOW,
            },
        )
        for key, task, user, content in (
            (
                "comment:requirement:mentor",
                submitted_task,
                mentor_1,
                "Em nhớ nêu rõ phạm vi hệ thống nhé.",
            ),
            (
                "comment:requirement:intern",
                submitted_task,
                users["intern_1"],
                "Em đã cập nhật phần phạm vi theo góp ý.",
            ),
            (
                "comment:database:mentor",
                revision_task,
                mentor_1,
                "Sơ đồ cần thể hiện rõ các quan hệ 1-n và n-n.",
            ),
        ):
            upsert_by(
                db,
                TaskComment,
                {"id": seed_id(key)},
                {"task_id": task.id, "user_id": user.id, "content": content, "created_at": NOW},
            )

        criteria_specs = (
            ("Chuyên môn", "Kiến thức và chất lượng thực hiện công việc.", 10, 40),
            ("Tiến độ", "Khả năng hoàn thành công việc đúng hạn.", 10, 30),
            ("Thái độ", "Tinh thần chủ động và phối hợp trong nhóm.", 10, 30),
        )
        criteria: list[EvaluationCriterion] = []
        for name, description, max_score, weight in criteria_specs:
            criteria.append(
                upsert_by(
                    db,
                    EvaluationCriterion,
                    {"name": name},
                    {
                        "description": description,
                        "max_score": max_score,
                        "weight": weight,
                        "status": "ACTIVE",
                    },
                )
            )
        db.flush()
        score_details = [
            {"criterion_id": str(criteria[0].id), "score": 8.5},
            {"criterion_id": str(criteria[1].id), "score": 9},
            {"criterion_id": str(criteria[2].id), "score": 9},
        ]
        upsert_seed(
            db,
            Evaluation,
            seed_id("evaluation:intern-1:periodic"),
            {
                "internship_member_id": members["intern_1"].id,
                "evaluation_type": "PERIODIC",
                "mentor_id": mentor_1.id,
                "criteria_scores": score_details,
                "total_score": 8.8,
                "comment": "Chủ động, có tiến bộ tốt trong giai đoạn đầu.",
                "status": "PUBLISHED",
                "published_at": NOW,
            },
        )
        upsert_seed(
            db,
            Evaluation,
            seed_id("evaluation:intern-2:periodic"),
            {
                "internship_member_id": members["intern_2"].id,
                "evaluation_type": "PERIODIC",
                "mentor_id": mentor_1.id,
                "criteria_scores": score_details,
                "total_score": 7.2,
                "comment": "Cần cải thiện tốc độ hoàn thành task.",
                "status": "DRAFT",
                "published_at": None,
            },
        )

        upsert_seed(
            db,
            InternshipRequest,
            seed_id("request:intern-4:extend"),
            {
                "internship_member_id": members["intern_4"].id,
                "type": "EXTEND",
                "requested_by": mentor_2.id,
                "reason": "Cần thêm thời gian để hoàn thành lộ trình backend.",
                "requested_end_date": date(2026, 12, 15),
                "status": "PENDING",
                "reviewed_by": None,
                "review_note": None,
                "reviewed_at": None,
            },
        )

        notification_specs = (
            (
                "all",
                "Chào mừng đợt thực tập 2026 - Thu",
                "Vui lòng hoàn thiện hồ sơ và xem lộ trình đào tạo.",
                "ALL",
                None,
            ),
            (
                "interns",
                "Cập nhật tài liệu Phase 2",
                "Tài liệu Angular cơ bản đã được bổ sung.",
                "ROLE",
                ["INTERN"],
            ),
            (
                "intern_1",
                "Task mới cần thực hiện",
                "Bạn có task Báo cáo phân tích yêu cầu cần hoàn thành.",
                "USER",
                [str(users["intern_1"].id)],
            ),
        )
        notifications: dict[str, Notification] = {}
        for key, title, content, target_type, target_data in notification_specs:
            notifications[key] = upsert_seed(
                db,
                Notification,
                seed_id(f"notification:{key}"),
                {
                    "title": title,
                    "content": content,
                    "target_type": target_type,
                    "target_data": target_data,
                    "created_by": admin.id,
                },
            )
        db.flush()
        for notification_key, user_key in (
            ("all", "intern_1"),
            ("interns", "intern_1"),
            ("all", "mentor_1"),
        ):
            upsert_by(
                db,
                NotificationRead,
                {
                    "notification_id": notifications[notification_key].id,
                    "user_id": users[user_key].id,
                },
                {"read_at": NOW},
            )

        conversation = upsert_seed(
            db,
            AIConversation,
            seed_id("conversation:intern-1:frontend-roadmap"),
            {"user_id": users["intern_1"].id, "title": "Hỏi về roadmap Frontend"},
        )
        db.flush()
        for key, role, content, citations in (
            ("user", "USER", "Phase Frontend có những nội dung nào?", None),
            (
                "assistant",
                "ASSISTANT",
                "Phase Frontend gồm Angular cơ bản và thiết kế giao diện với NG-ZORRO.",
                [{"source": "Lộ trình Full-stack 2026", "section": "Giai đoạn 2"}],
            ),
        ):
            upsert_by(
                db,
                AIMessage,
                {"id": seed_id(f"message:intern-1:frontend-roadmap:{key}")},
                {
                    "conversation_id": conversation.id,
                    "role": role,
                    "content": content,
                    "citations": citations,
                    "created_at": NOW,
                },
            )

    print("Seeded ITMS development data for all 20 business tables.")
    print("Demo accounts:")
    for _, email, password, _, _ in DEMO_USERS:
        print(f"- {email} / {password}")


if __name__ == "__main__":
    main()
