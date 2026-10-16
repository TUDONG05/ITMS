import json
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.errors import ApiError
from app.core.settings import get_settings
from app.db.session import get_session_factory
from app.main import app
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.models.evaluation import Evaluation
from app.models.exam import Quiz, QuizAttempt
from app.models.interaction import Notification, NotificationRead
from app.models.internship import Internship, InternshipMember
from app.models.knowledge import AIConversation, AIMessage
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.task import Task
from app.models.user import User
from app.services.assistant import SYSTEM_PROMPT, AssistantService
from app.services.assistant_tools import (
    TOOL_DEFINITIONS,
    AssistantToolService,
    AuthorizedScopeService,
)


@pytest.fixture
def assistant_data() -> Generator[dict[str, object]]:
    session = get_session_factory()()
    suffix = uuid.uuid4().hex[:8]
    admin = User(
        email=f"ai_admin_{suffix}@example.com",
        password_hash="hash",
        full_name="AI Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    mentor = User(
        email=f"ai_mentor_{suffix}@example.com",
        password_hash="hash",
        full_name="AI Mentor",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_b = User(
        email=f"ai_mentor_b_{suffix}@example.com",
        password_hash="hash",
        full_name="AI Mentor B",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern_a = User(
        email=f"ai_intern_a_{suffix}@example.com",
        password_hash="hash",
        full_name="AI Intern A",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_b = User(
        email=f"ai_intern_b_{suffix}@example.com",
        password_hash="hash",
        full_name="AI Intern B",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    users = [admin, mentor, mentor_b, intern_a, intern_b]
    session.add_all(users)
    session.flush()
    internship = Internship(
        name=f"AI Batch {suffix}",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=InternshipStatus.ONGOING,
        created_by=admin.id,
    )
    session.add(internship)
    session.flush()
    roadmap = Roadmap(
        name=f"AI Roadmap {suffix}",
        status="ACTIVE",
        created_by=admin.id,
    )
    session.add(roadmap)
    session.flush()
    phase = Phase(roadmap_id=roadmap.id, name="AI Phase", order_no=1)
    session.add(phase)
    session.flush()
    content = LearningContent(
        phase_id=phase.id,
        title="AI Content",
        type="LESSON",
        order_no=1,
    )
    session.add(content)
    session.flush()
    quiz = Quiz(
        phase_id=phase.id,
        title="AI Quiz",
        duration_minutes=30,
        pass_score=60,
        max_attempts=2,
        status="PUBLISHED",
    )
    session.add(quiz)
    session.flush()
    member_a = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_a.id,
        mentor_id=mentor.id,
        roadmap_id=roadmap.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor_b.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add_all([member_a, member_b])
    session.flush()
    progress = LearningProgress(
        internship_member_id=member_a.id,
        content_id=content.id,
        status="IN_PROGRESS",
        progress_percent=50,
    )
    session.add(progress)
    own_task = Task(
        internship_member_id=member_a.id,
        created_by=mentor.id,
        title="Task visible to intern A",
        status="TODO",
        deadline=datetime.now(UTC) + timedelta(days=2),
    )
    foreign_task = Task(
        internship_member_id=member_b.id,
        created_by=mentor_b.id,
        title="Secret task of intern B",
        status="TODO",
        deadline=datetime.now(UTC) + timedelta(days=3),
    )
    session.add_all([own_task, foreign_task])
    quiz_attempt = QuizAttempt(
        quiz_id=quiz.id,
        internship_member_id=member_a.id,
        attempt_no=1,
        answers=[{"question_id": "secret", "selected_keys": ["A"]}],
        score=85,
        passed=True,
        submitted_at=datetime.now(UTC),
    )
    session.add(quiz_attempt)
    published_evaluation = Evaluation(
        internship_member_id=member_a.id,
        mentor_id=mentor.id,
        evaluation_type="PERIODIC",
        criteria_scores=[],
        total_score=8.5,
        comment="A" * 3000,
        status="PUBLISHED",
        published_at=datetime.now(UTC),
    )
    draft_evaluation = Evaluation(
        internship_member_id=member_a.id,
        mentor_id=mentor.id,
        evaluation_type="FINAL",
        criteria_scores=[],
        total_score=9,
        comment="Bản nháp nội bộ",
        status="DRAFT",
    )
    session.add_all([published_evaluation, draft_evaluation])
    session.commit()
    yield {
        "session": session,
        "users": users,
        "admin": admin,
        "mentor": mentor,
        "mentor_b": mentor_b,
        "intern_a": intern_a,
        "intern_b": intern_b,
        "members": [member_a, member_b],
        "internship": internship,
        "quiz": quiz,
        "roadmap": roadmap,
        "progress": progress,
        "evaluations": [published_evaluation, draft_evaluation],
    }
    user_ids = [user.id for user in users]
    conversation_ids = list(
        session.scalars(
            AIConversation.__table__.select()
            .with_only_columns(AIConversation.id)
            .where(AIConversation.user_id.in_(user_ids))
        )
    )
    if conversation_ids:
        session.query(AIMessage).filter(AIMessage.conversation_id.in_(conversation_ids)).delete(
            synchronize_session=False
        )
        session.query(AIConversation).filter(AIConversation.id.in_(conversation_ids)).delete(
            synchronize_session=False
        )
    session.query(Evaluation).filter(
        Evaluation.internship_member_id.in_([member_a.id, member_b.id])
    ).delete(synchronize_session=False)
    session.query(QuizAttempt).filter(
        QuizAttempt.internship_member_id.in_([member_a.id, member_b.id])
    ).delete(synchronize_session=False)
    session.query(LearningProgress).filter(
        LearningProgress.internship_member_id.in_([member_a.id, member_b.id])
    ).delete(synchronize_session=False)
    session.query(Task).filter(Task.internship_member_id.in_([member_a.id, member_b.id])).delete(
        synchronize_session=False
    )
    session.query(InternshipMember).filter(
        InternshipMember.id.in_([member_a.id, member_b.id])
    ).delete(synchronize_session=False)
    session.delete(quiz)
    session.delete(content)
    session.delete(phase)
    session.delete(roadmap)
    session.delete(internship)
    session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture
def assistant_notification_data(
    assistant_data: dict[str, object],
) -> Generator[dict[str, object]]:
    session = assistant_data["session"]
    admin = assistant_data["admin"]
    intern_a = assistant_data["intern_a"]
    intern_b = assistant_data["intern_b"]
    now = datetime.now(UTC)
    notifications = [
        Notification(
            title="Global notice",
            content="Visible to everyone",
            target_type="ALL",
            target_data=None,
            created_by=admin.id,
            created_at=now,
        ),
        Notification(
            title="Intern notice",
            content="Visible to interns",
            target_type="ROLE",
            target_data=["INTERN"],
            created_by=admin.id,
            created_at=now + timedelta(seconds=1),
        ),
        Notification(
            title="Mentor notice",
            content="Visible to mentors",
            target_type="ROLE",
            target_data=["MENTOR"],
            created_by=admin.id,
            created_at=now + timedelta(seconds=2),
        ),
        Notification(
            title="Private notice for intern B",
            content="Visible only to intern B",
            target_type="USER",
            target_data=[str(intern_b.id)],
            created_by=admin.id,
            created_at=now + timedelta(seconds=3),
        ),
    ]
    session.add_all(notifications)
    session.flush()
    session.add(NotificationRead(notification_id=notifications[0].id, user_id=intern_a.id))
    session.flush()

    yield {**assistant_data, "notifications": notifications}

    session.query(NotificationRead).filter(
        NotificationRead.notification_id.in_([item.id for item in notifications])
    ).delete(synchronize_session=False)
    session.query(Notification).filter(Notification.created_by == admin.id).delete(
        synchronize_session=False
    )
    session.flush()


def test_intern_chat_ignores_foreign_intern_id_and_returns_contract(
    monkeypatch: pytest.MonkeyPatch, assistant_data: dict[str, object]
) -> None:
    intern_a = assistant_data["intern_a"]
    intern_b = assistant_data["intern_b"]
    captured_requests: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def fake_post(_url: str, **kwargs: object) -> FakeResponse:
        request_json = kwargs["json"]
        assert isinstance(request_json, dict)
        captured_requests.append(request_json)
        if len(captured_requests) == 1:
            return FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_tasks",
                                        "type": "function",
                                        "function": {
                                            "name": "get_tasks",
                                            "arguments": json.dumps(
                                                {"intern_id": str(intern_b.id), "limit": 10}
                                            ),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Bạn có một task đang chờ xử lý.",
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv("ITMS_AI_API_KEY", "test-key")
    monkeypatch.setenv("ITMS_AI_BASE_URL", "https://ai.example.test/v1")
    monkeypatch.setenv("ITMS_AI_MODEL", "test-model")
    get_settings.cache_clear()
    monkeypatch.setattr(httpx, "post", fake_post)

    response = TestClient(app).post(
        "/api/v1/assistant/chat",
        headers={"X-User-Id": str(intern_a.id)},
        json={"message": "Task của tôi là gì?"},
    )

    get_settings.cache_clear()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversation_id"]
    assert body["message"]["role"] == "ASSISTANT"
    assert body["message"]["content"] == "Bạn có một task đang chờ xử lý."
    assert len(captured_requests) == 2
    assert captured_requests[0]["max_tokens"] == 600
    tool_context = json.dumps(captured_requests[1], ensure_ascii=False)
    assert "Task visible to intern A" in tool_context
    assert "Secret task of intern B" not in tool_context

    conversations = TestClient(app).get(
        "/api/v1/assistant/conversations",
        headers={"X-User-Id": str(intern_a.id)},
    )
    assert conversations.status_code == 200
    assert conversations.json()[0]["id"] == body["conversation_id"]

    detail_url = f"/api/v1/assistant/conversations/{body['conversation_id']}"
    detail = TestClient(app).get(detail_url, headers={"X-User-Id": str(intern_a.id)})
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "USER",
        "ASSISTANT",
    ]
    assistant_message = detail.json()["messages"][1]
    assert assistant_message["citations"][0]["intern_ids"] == [str(intern_a.id)]

    forbidden = TestClient(app).get(detail_url, headers={"X-User-Id": str(intern_b.id)})
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"


def test_notification_tool_is_exposed_and_scopes_intern_notifications(
    assistant_notification_data: dict[str, object],
) -> None:
    session = assistant_notification_data["session"]
    intern = assistant_notification_data["intern_a"]
    tool_names = {item["function"]["name"] for item in TOOL_DEFINITIONS}

    result = AssistantToolService().execute(
        session, intern, "get_notifications", {"query": "notice"}
    )

    assert "get_notifications" in tool_names
    assert result["scope"] == "RECEIVED"
    assert result["total_count"] == 2
    assert result["unread_count"] == 1
    assert result["returned_count"] == 2
    assert result["truncated"] is False
    assert {item["title"] for item in result["notifications"]} == {
        "Global notice",
        "Intern notice",
    }
    assert all("target_data" not in item for item in result["notifications"])
    assert all("created_by" not in item for item in result["notifications"])


def test_notification_tool_applies_mentor_and_admin_scope(
    assistant_notification_data: dict[str, object],
) -> None:
    session = assistant_notification_data["session"]
    mentor = assistant_notification_data["mentor"]
    admin = assistant_notification_data["admin"]
    service = AssistantToolService()

    mentor_result = service.execute(session, mentor, "get_notifications", {"query": "notice"})
    admin_result = service.execute(session, admin, "get_notifications", {"query": "notice"})

    assert mentor_result["scope"] == "RECEIVED"
    assert {item["title"] for item in mentor_result["notifications"]} == {
        "Global notice",
        "Mentor notice",
    }
    assert mentor_result["unread_count"] == 2
    assert admin_result["scope"] == "ALL_SENT"
    assert admin_result["total_count"] == 4
    assert admin_result["unread_count"] is None
    assert {item["title"] for item in admin_result["notifications"]} == {
        "Global notice",
        "Intern notice",
        "Mentor notice",
        "Private notice for intern B",
    }
    assert all("read_count" in item for item in admin_result["notifications"])
    assert all("target_data" not in item for item in admin_result["notifications"])


def test_notification_tool_filters_unread_and_reports_exact_limited_total(
    assistant_notification_data: dict[str, object],
) -> None:
    session = assistant_notification_data["session"]
    admin = assistant_notification_data["admin"]
    intern = assistant_notification_data["intern_a"]
    now = datetime.now(UTC) + timedelta(minutes=1)
    extra_notifications = [
        Notification(
            title=f"Count notice {index}",
            content="Counted notification",
            target_type="ALL",
            target_data=None,
            created_by=admin.id,
            created_at=now + timedelta(seconds=index),
        )
        for index in range(21)
    ]
    session.add_all(extra_notifications)
    session.flush()
    service = AssistantToolService()

    limited = service.execute(
        session,
        intern,
        "get_notifications",
        {"query": "Count notice", "limit": 20},
    )
    unread = service.execute(
        session,
        intern,
        "get_notifications",
        {"query": "Intern notice", "status": "UNREAD"},
    )

    assert limited["total_count"] == 21
    assert limited["returned_count"] == 20
    assert limited["truncated"] is True
    assert unread["total_count"] == 1
    assert unread["returned_count"] == 1
    assert unread["notifications"][0]["title"] == "Intern notice"


def test_task_tool_applies_role_scope(assistant_data: dict[str, object]) -> None:
    session = assistant_data["session"]
    admin = assistant_data["admin"]
    mentor = assistant_data["mentor"]
    intern_a = assistant_data["intern_a"]
    intern_b = assistant_data["intern_b"]
    tools = AssistantToolService()

    intern_result = tools.get_tasks(
        session,
        intern_a,
        {"intern_id": str(intern_b.id), "limit": 20},
    )
    assert [task["title"] for task in intern_result["tasks"]] == ["Task visible to intern A"]

    with pytest.raises(ApiError) as denied:
        tools.get_tasks(session, mentor, {"intern_id": str(intern_b.id)})
    assert denied.value.status_code == 404

    admin_result = tools.get_tasks(
        session,
        admin,
        {"intern_id": str(intern_b.id), "limit": 20},
    )
    assert [task["title"] for task in admin_result["tasks"]] == ["Secret task of intern B"]
    assert admin_result["tasks"][0]["intern_id"] == str(intern_b.id)
    assert admin_result["tasks"][0]["intern_name"] == "AI Intern B"

    mentor_search = tools.find_accessible_interns(session, mentor, {"query": "AI Intern"})
    assert [item["intern_id"] for item in mentor_search["interns"]] == [str(intern_a.id)]
    assert "email" not in mentor_search["interns"][0]


def test_intern_search_reports_exact_total_when_results_hit_the_row_limit(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    admin = assistant_data["admin"]
    internship = assistant_data["internship"]
    suffix = uuid.uuid4().hex[:8]
    query = f"Count Probe {suffix}"
    interns = [
        User(
            email=f"count_probe_{suffix}_{index}@example.invalid",
            password_hash="not-a-real-password",
            full_name=f"{query} {index:02d}",
            role=UserRole.INTERN,
            status=UserStatus.ACTIVE,
        )
        for index in range(21)
    ]
    session.add_all(interns)
    session.flush()
    session.add_all(
        [
            InternshipMember(
                internship_id=internship.id,
                intern_id=intern.id,
                status=InternshipMemberStatus.ACTIVE,
            )
            for intern in interns
        ]
    )
    session.flush()

    result = AssistantToolService().find_accessible_interns(
        session,
        admin,
        {"query": query, "limit": 20},
    )

    assert result["total_count"] == 21
    assert result["returned_count"] == 20
    assert result["truncated"] is True
    assert len(result["interns"]) == 20


def test_mentor_assignment_tool_is_exposed_and_returns_interns_own_mentor(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    intern_a = assistant_data["intern_a"]
    intern_b = assistant_data["intern_b"]

    tool_names = {item["function"]["name"] for item in TOOL_DEFINITIONS}
    assert "get_mentor_assignment" in tool_names

    result = AssistantToolService().execute(
        session,
        intern_a,
        "get_mentor_assignment",
        {"intern_id": str(intern_b.id)},
    )

    assert result == {
        "assignments": [
            {
                "intern_id": str(intern_a.id),
                "intern_name": "AI Intern A",
                "mentor_id": str(assistant_data["mentor"].id),
                "mentor_name": "AI Mentor",
                "internship": assistant_data["internship"].name,
                "member_status": "ACTIVE",
            }
        ]
    }


def test_mentor_assignment_tool_applies_mentor_and_admin_scope(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    admin = assistant_data["admin"]
    mentor = assistant_data["mentor"]
    intern_b = assistant_data["intern_b"]
    tools = AssistantToolService()

    with pytest.raises(ApiError) as denied:
        tools.execute(
            session,
            mentor,
            "get_mentor_assignment",
            {"intern_id": str(intern_b.id)},
        )
    assert denied.value.status_code == 404

    result = tools.execute(
        session,
        admin,
        "get_mentor_assignment",
        {"intern_id": str(intern_b.id)},
    )

    assert result["assignments"][0]["mentor_name"] == "AI Mentor B"
    assert result["assignments"][0]["intern_id"] == str(intern_b.id)
    assert "email" not in result["assignments"][0]


def test_task_tool_reports_exact_total_when_rows_are_limited(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    mentor = assistant_data["mentor"]
    intern = assistant_data["intern_a"]
    member = assistant_data["members"][0]
    session.add_all(
        [
            Task(
                internship_member_id=member.id,
                created_by=mentor.id,
                title=f"Extra task {index}",
                status="TODO",
            )
            for index in range(2)
        ]
    )
    session.flush()

    result = AssistantToolService().get_tasks(
        session,
        intern,
        {"status": "TODO", "limit": 1},
    )

    assert result["total_count"] == 3
    assert result["returned_count"] == 1
    assert result["truncated"] is True


def test_learning_progress_uses_partial_percentages(
    assistant_data: dict[str, object],
) -> None:
    result = AssistantToolService().get_learning_progress(
        assistant_data["session"],
        assistant_data["intern_a"],
        {},
    )

    assert result["progress"][0]["progress_percent"] == 50.0


def test_intern_cannot_read_inactive_roadmap(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    roadmap = assistant_data["roadmap"]
    roadmap.status = "DRAFT"
    session.flush()

    result = AssistantToolService().get_roadmap(
        session,
        assistant_data["intern_a"],
        {},
    )

    assert result["roadmaps"] == []
    roadmap.status = "ACTIVE"
    session.flush()


def test_evaluation_tool_hides_drafts_from_intern(assistant_data: dict[str, object]) -> None:
    session = assistant_data["session"]
    intern = assistant_data["intern_a"]
    mentor = assistant_data["mentor"]
    admin = assistant_data["admin"]
    tools = AssistantToolService()

    intern_result = tools.get_evaluations(session, intern, {})
    assert [item["status"] for item in intern_result["evaluations"]] == ["PUBLISHED"]
    assert "Bản nháp nội bộ" not in str(intern_result)
    assert len(intern_result["evaluations"][0]["comment"]) <= 2000

    mentor_result = tools.get_evaluations(session, mentor, {})
    assert {item["status"] for item in mentor_result["evaluations"]} == {
        "DRAFT",
        "PUBLISHED",
    }

    admin_result = tools.get_evaluations(
        session,
        admin,
        {"intern_id": str(intern.id)},
    )
    assert len(admin_result["evaluations"]) == 2
    assert {item["intern_id"] for item in admin_result["evaluations"]} == {str(intern.id)}


def test_quiz_tool_never_returns_answers(assistant_data: dict[str, object]) -> None:
    session = assistant_data["session"]
    intern = assistant_data["intern_a"]
    tools = AssistantToolService()

    result = tools.get_quiz_results(session, intern, {})

    assert result["correct_answers_included"] is False
    assert result["quiz_results"][0]["score"] == 85
    quiz_result = result["quiz_results"][0]
    assert quiz_result["intern_id"] == str(intern.id)
    assert "answers" not in quiz_result
    assert "correct_answer" not in quiz_result


def test_history_masks_data_after_mentor_scope_is_revoked(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    mentor = assistant_data["mentor"]
    mentor_b = assistant_data["mentor_b"]
    intern = assistant_data["intern_a"]
    member = assistant_data["members"][0]
    conversation = AIConversation(user_id=mentor.id, title="Lich su co RBAC")
    session.add(conversation)
    session.flush()
    session.add_all(
        [
            AIMessage(
                conversation_id=conversation.id,
                role="USER",
                content="Task cua intern nay la gi?",
            ),
            AIMessage(
                conversation_id=conversation.id,
                role="ASSISTANT",
                content="Noi dung nhay cam cua intern.",
                citations=[
                    {
                        "type": "database",
                        "tool": "get_tasks",
                        "label": "Task trong ITMS",
                        "intern_ids": [str(intern.id)],
                    }
                ],
            ),
        ]
    )
    session.commit()

    member.mentor_id = mentor_b.id
    session.commit()

    response = TestClient(app).get(
        f"/api/v1/assistant/conversations/{conversation.id}",
        headers={"X-User-Id": str(mentor.id)},
    )

    assert response.status_code == 200
    assistant_message = response.json()["messages"][1]
    assert assistant_message["content"] == (
        "Noi dung nay khong con kha dung do pham vi truy cap da thay doi."
    )
    assert assistant_message["citations"] is None


def test_tool_data_is_not_sent_to_provider_when_scope_changes(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    mentor = assistant_data["mentor"]
    mentor_b = assistant_data["mentor_b"]
    intern = assistant_data["intern_a"]
    member = assistant_data["members"][0]

    class ToolCallingClient:
        calls = 0

        def complete(self, _messages: list[dict]) -> dict:
            self.calls += 1
            if self.calls > 1:
                pytest.fail("Tool data must not be sent after the RBAC scope changes")
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_tasks",
                        "type": "function",
                        "function": {
                            "name": "get_tasks",
                            "arguments": json.dumps({"intern_id": str(intern.id)}),
                        },
                    },
                    {
                        "id": "call_tasks_again",
                        "type": "function",
                        "function": {
                            "name": "get_tasks",
                            "arguments": json.dumps({"intern_id": str(intern.id)}),
                        },
                    },
                ],
            }

    class ScopeChangingTools(AssistantToolService):
        calls = 0

        def execute(self, db, user, name, arguments):
            self.calls += 1
            result = super().execute(db, user, name, arguments)
            member.mentor_id = mentor_b.id
            db.flush()
            return result

    initial_scope = AuthorizedScopeService.fingerprint(session, mentor)
    service = AssistantService(client=ToolCallingClient(), tools=ScopeChangingTools())

    with pytest.raises(ApiError) as changed:
        service._run_tool_loop(
            session,
            mentor,
            [{"role": "user", "content": "Task cua intern nay?"}],
            [],
            initial_scope,
        )

    assert changed.value.status_code == 409
    assert changed.value.code == "AI_SCOPE_CHANGED"
    assert service.tools.calls == 1
    session.rollback()


def test_stale_user_role_is_rejected_before_querying_tools(
    assistant_data: dict[str, object],
) -> None:
    session = assistant_data["session"]
    mentor = assistant_data["mentor"]
    stale_user = User(
        id=mentor.id,
        email=mentor.email,
        password_hash=mentor.password_hash,
        full_name=mentor.full_name,
        role=UserRole.ADMIN,
        status=mentor.status,
    )

    with pytest.raises(ApiError) as changed:
        AuthorizedScopeService.assert_current_user(session, stale_user)

    assert changed.value.status_code == 409
    assert changed.value.code == "AI_SCOPE_CHANGED"


def test_database_answer_requires_a_successful_tool(
    assistant_data: dict[str, object],
) -> None:
    class ContentOnlyClient:
        def complete(self, _messages: list[dict]) -> dict:
            return {"role": "assistant", "content": "Ban co 999 task."}

    session = assistant_data["session"]
    intern = assistant_data["intern_a"]
    initial_scope = AuthorizedScopeService.fingerprint(session, intern)
    service = AssistantService(client=ContentOnlyClient())

    with pytest.raises(ApiError) as missing_source:
        service._run_tool_loop(
            session,
            intern,
            [{"role": "user", "content": "Toi co bao nhieu task?"}],
            [],
            initial_scope,
        )

    assert missing_source.value.code == "AI_DATABASE_SOURCE_REQUIRED"


def test_system_prompt_routes_aggregate_questions_without_intern_lookup() -> None:
    assert "câu hỏi tổng hợp" in SYSTEM_PROMPT
    assert "không truyền intern_id" in SYSTEM_PROMPT


def test_system_prompt_distinguishes_exact_totals_from_limited_rows() -> None:
    assert "total_count" in SYSTEM_PROMPT
    assert "returned_count" in SYSTEM_PROMPT


def test_malformed_provider_tool_calls_return_a_safe_error(
    assistant_data: dict[str, object],
) -> None:
    class MalformedClient:
        def complete(self, _messages: list[dict]) -> dict:
            return {"role": "assistant", "content": None, "tool_calls": ["invalid"]}

    session = assistant_data["session"]
    intern = assistant_data["intern_a"]
    initial_scope = AuthorizedScopeService.fingerprint(session, intern)

    with pytest.raises(ApiError) as provider_error:
        AssistantService(client=MalformedClient())._run_tool_loop(
            session,
            intern,
            [{"role": "user", "content": "Task cua toi?"}],
            [],
            initial_scope,
        )

    assert provider_error.value.code == "AI_PROVIDER_UNAVAILABLE"


def test_five_parallel_tool_calls_fit_within_total_tool_budget(
    assistant_data: dict[str, object],
) -> None:
    class ParallelToolClient:
        calls = 0

        def complete(self, _messages: list[dict]) -> dict:
            self.calls += 1
            if self.calls == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_tasks_{index}",
                            "type": "function",
                            "function": {"name": "get_tasks", "arguments": "{}"},
                        }
                        for index in range(5)
                    ],
                }
            return {"role": "assistant", "content": "Đã kiểm tra dữ liệu."}

    class CountingTools(AssistantToolService):
        calls = 0

        def execute(self, _db, _user, _name, _arguments):
            self.calls += 1
            return {"tasks": [], "total_count": 0}

    session = assistant_data["session"]
    intern = assistant_data["intern_a"]
    citations: list[dict] = []
    initial_scope = AuthorizedScopeService.fingerprint(session, intern)
    tools = CountingTools()

    content = AssistantService(
        client=ParallelToolClient(),
        tools=tools,
    )._run_tool_loop(
        session,
        intern,
        [{"role": "user", "content": "Kiểm tra các task."}],
        citations,
        initial_scope,
    )

    assert content == "Đã kiểm tra dữ liệu."
    assert tools.calls == 5


def test_empty_tool_result_keeps_authorized_subject_in_citation(
    assistant_data: dict[str, object],
) -> None:
    intern = assistant_data["intern_a"]

    class EmptyResultClient:
        calls = 0

        def complete(self, _messages: list[dict]) -> dict:
            self.calls += 1
            if self.calls == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_tasks",
                            "type": "function",
                            "function": {"name": "get_tasks", "arguments": "{}"},
                        }
                    ],
                }
            return {"role": "assistant", "content": "Ban khong co task."}

    class EmptyTools(AssistantToolService):
        def execute(self, _db, _user, _name, _arguments):
            return {"tasks": [], "total_count": 0}

    session = assistant_data["session"]
    citations: list[dict] = []
    initial_scope = AuthorizedScopeService.fingerprint(session, intern)

    content = AssistantService(
        client=EmptyResultClient(),
        tools=EmptyTools(),
    )._run_tool_loop(
        session,
        intern,
        [{"role": "user", "content": "Task cua toi?"}],
        citations,
        initial_scope,
    )

    assert content == "Ban khong co task."
    assert citations[0]["intern_ids"] == [str(intern.id)]
    assert citations[0]["scope_role"] == "INTERN"
