import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.models.internship import Internship, InternshipMember
from app.models.task import Task, TaskAssignee
from app.models.user import User
from app.services.assistant_tools import AssistantToolService
from app.services.dashboard import DashboardService


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def task_test_data() -> Generator[dict]:
    factory = get_session_factory()
    session = factory()
    suffix = uuid.uuid4().hex[:8]

    admin = User(
        email=f"t_admin_{suffix}@ex.com",
        password_hash="h",
        full_name="Admin T",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    mentor_a = User(
        email=f"t_ma_{suffix}@ex.com",
        password_hash="h",
        full_name="Mentor A",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_b = User(
        email=f"t_mb_{suffix}@ex.com",
        password_hash="h",
        full_name="Mentor B",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern_a = User(
        email=f"t_ia_{suffix}@ex.com",
        password_hash="h",
        full_name="Intern A",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_b = User(
        email=f"t_ib_{suffix}@ex.com",
        password_hash="h",
        full_name="Intern B",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    session.add_all([admin, mentor_a, mentor_b, intern_a, intern_b])
    session.commit()

    internship = Internship(
        name=f"TBatch {suffix}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipStatus.ONGOING,
        created_by=admin.id,
    )
    session.add(internship)
    session.commit()

    member_a = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_a.id,
        mentor_id=mentor_a.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor_b.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add_all([member_a, member_b])
    session.commit()
    data = {
        "admin": admin,
        "mentor_a": mentor_a,
        "mentor_b": mentor_b,
        "intern_a": intern_a,
        "intern_b": intern_b,
        "member_a": member_a,
        "member_b": member_b,
        "internship": internship,
    }
    yield data
    session.rollback()
    session.close()


def _create_task(client, mentor, member_id, title="Task 1"):
    deadline = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    resp = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(mentor.id)},
        json={
            "internship_member_id": str(member_id),
            "title": title,
            "description": "Mô tả task",
            "deadline": deadline,
            "priority": "HIGH",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _shareable_members(task_test_data):
    """Give the fixture's second member to the same mentor for shared-task tests."""
    with get_session_factory()() as session:
        member = session.get(InternshipMember, task_test_data["member_b"].id)
        member.mentor_id = task_test_data["mentor_a"].id
        session.commit()
    return [str(task_test_data[key].id) for key in ("member_a", "member_b")]


def test_shared_task_is_one_record_visible_to_every_assignee(client, task_test_data):
    ids = _shareable_members(task_test_data)
    mentor = task_test_data["mentor_a"]
    response = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(mentor.id)},
        json={
            "title": "Shared group task",
            "internship_member_ids": ids + ids,
            "deadline": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    task = response.json()
    assert set(task["internship_member_ids"]) == set(ids)
    assert {a["intern_name"] for a in task["assignees"]} == {"Intern A", "Intern B"}
    with get_session_factory()() as session:
        assert session.query(Task).filter(Task.id == uuid.UUID(task["id"])).count() == 1
        assert (
            session.query(TaskAssignee)
            .filter(TaskAssignee.task_id == uuid.UUID(task["id"]))
            .count()
            == 2
        )
        member_ids = [uuid.UUID(member_id) for member_id in ids]
        assert DashboardService._tasks(session, member_ids).count() == 1
        tools = AssistantToolService()
        tasks = tools.get_tasks(session, mentor, {})
        deadlines = tools.get_deadlines(session, mentor, {})
        assert tasks["total_count"] == deadlines["total_count"] == 1
        assert tasks["returned_count"] == deadlines["returned_count"] == 1
        assert {a["intern_name"] for a in tasks["tasks"][0]["assignees"]} == {
            "Intern A",
            "Intern B",
        }
    for role in ("intern_a", "intern_b", "mentor_a"):
        headers = {"X-User-Id": str(task_test_data[role].id)}
        detail = client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == task["id"]
        assert len(detail.json()["assignees"]) == 2
        listing = client.get("/api/v1/tasks", headers=headers).json()
        assert sum(t["id"] == task["id"] for t in listing) == 1
    denied = client.get(
        f"/api/v1/tasks/{task['id']}",
        headers={"X-User-Id": str(task_test_data["mentor_b"].id)},
    )
    assert denied.status_code == 403


def test_shared_assignment_rejects_foreign_member_atomically(client, task_test_data):
    title = "Foreign recipient must prevent creation"
    ids = [str(task_test_data[key].id) for key in ("member_a", "member_b")]
    response = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(task_test_data["mentor_a"].id)},
        json={"title": title, "internship_member_ids": ids},
    )
    assert response.status_code == 403
    with get_session_factory()() as session:
        assert session.query(Task).filter(Task.title == title).count() == 0


def test_shared_task_search_and_filters_include_every_assignee(client, task_test_data):
    ids = _shareable_members(task_test_data)
    headers = {"X-User-Id": str(task_test_data["mentor_a"].id)}
    created = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Shared search task", "internship_member_ids": ids},
    ).json()
    for params in (
        {"search": "Intern B"},
        {"member_id": ids[1]},
        {"internship_id": str(task_test_data["internship"].id)},
    ):
        listing = client.get("/api/v1/tasks", headers=headers, params=params)
        assert listing.status_code == 200
        assert sum(t["id"] == created["id"] for t in listing.json()) == 1


def test_shared_task_requires_a_nonempty_recipient_list(client, task_test_data):
    headers = {"X-User-Id": str(task_test_data["mentor_a"].id)}
    for recipient in ({"internship_member_ids": []}, {"internship_member_ids": None}, {}):
        response = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "No recipients", **recipient}
        )
        assert response.status_code == 422


def test_group_mode_shares_one_submission_and_review(client, task_test_data):
    ids = _shareable_members(task_test_data)
    headers = {
        key: {"X-User-Id": str(task_test_data[key].id)}
        for key in ("mentor_a", "intern_a", "intern_b")
    }
    task = client.post(
        "/api/v1/tasks",
        headers=headers["mentor_a"],
        json={
            "title": "Group mode",
            "internship_member_ids": ids,
            "assignment_mode": "GROUP",
        },
    ).json()
    url = f"/api/v1/tasks/{task['id']}"
    first = client.post(
        url + "/submit", headers=headers["intern_a"], json={"content": "First draft"}
    )
    second = client.post(
        url + "/submit", headers=headers["intern_b"], json={"content": "Group final"}
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["internship_member_id"] is None
    for intern in ("intern_a", "intern_b"):
        detail = client.get(url, headers=headers[intern]).json()
        assert len(detail["submissions"]) == 1
        assert detail["submissions"][0]["content"] == "Group final"
    review = client.post(
        url + "/review", headers=headers["mentor_a"], json={"decision": "COMPLETED"}
    )
    assert review.status_code == 200
    detail = client.get(url, headers=headers["intern_b"]).json()
    assert detail["status"] == "COMPLETED"
    assert {a["status"] for a in detail["assignees"]} == {"COMPLETED"}


def test_individual_mode_scopes_submissions_and_completes_only_when_all_reviewed(
    client, task_test_data
):
    ids = _shareable_members(task_test_data)
    headers = {
        key: {"X-User-Id": str(task_test_data[key].id)}
        for key in ("mentor_a", "intern_a", "intern_b")
    }
    task = client.post(
        "/api/v1/tasks",
        headers=headers["mentor_a"],
        json={
            "title": "Individual mode",
            "internship_member_ids": ids,
            "assignment_mode": "INDIVIDUAL",
            "deadline": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert task["assignment_mode"] == "INDIVIDUAL"
    url = f"/api/v1/tasks/{task['id']}"
    first = client.post(url + "/submit", headers=headers["intern_a"], json={"content": "A private"})
    assert first.status_code == 200
    assert first.json()["internship_member_id"] == ids[0]
    assert first.json()["intern_name"] == "Intern A"
    assert client.get(url, headers=headers["intern_b"]).json()["submissions"] == []
    assert client.delete(url + "/submission", headers=headers["intern_b"]).status_code == 404
    second = client.post(
        url + "/submit", headers=headers["intern_b"], json={"content": "B private"}
    )
    assert second.status_code == 200
    assert second.json()["id"] != first.json()["id"]
    assert len(client.get(url, headers=headers["mentor_a"]).json()["submissions"]) == 2
    assert (
        client.post(
            url + "/review", headers=headers["mentor_a"], json={"decision": "COMPLETED"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            url + "/review",
            headers=headers["mentor_a"],
            json={
                "decision": "COMPLETED",
                "internship_member_id": str(uuid.uuid4()),
            },
        ).status_code
        == 400
    )
    reviewed = client.post(
        url + "/review",
        headers=headers["mentor_a"],
        json={
            "decision": "COMPLETED",
            "internship_member_id": ids[0],
        },
    )
    assert reviewed.status_code == 200
    a_detail = client.get(url, headers=headers["intern_a"]).json()
    assert a_detail["status"] == "SUBMITTED"
    assert not a_detail["is_overdue"]
    assert len(a_detail["submissions"]) == 1
    assert a_detail["submissions"][0]["content"] == "A private"
    dashboard = client.get("/api/v1/dashboard", headers=headers["intern_a"])
    assert dashboard.status_code == 200
    assert dashboard.json()["task_breakdown"]["completed"] == 1
    assert dashboard.json()["task_breakdown"]["overdue"] == 0
    assert dashboard.json()["recent_items"][0]["status"] == "COMPLETED"
    with get_session_factory()() as session:
        tools = AssistantToolService()
        tasks = tools.get_tasks(session, task_test_data["intern_a"], {"status": "COMPLETED"})
        deadlines = tools.get_deadlines(session, task_test_data["intern_a"], {"range": "OVERDUE"})
        assert tasks["total_count"] == 1
        assert tasks["tasks"][0]["status"] == "COMPLETED"
        assert deadlines["total_count"] == 0
    assert (
        client.post(
            url + "/submit", headers=headers["intern_a"], json={"content": "Overwrite accepted"}
        ).status_code
        == 400
    )
    assert client.delete(url + "/submission", headers=headers["intern_a"]).status_code == 400
    completed = client.get(
        "/api/v1/tasks", headers=headers["intern_a"], params={"status": "COMPLETED"}
    ).json()
    assert any(t["id"] == task["id"] for t in completed)
    overdue = client.get(
        "/api/v1/tasks", headers=headers["intern_a"], params={"overdue": True}
    ).json()
    assert not any(t["id"] == task["id"] for t in overdue)
    revision = client.post(
        url + "/review",
        headers=headers["mentor_a"],
        json={
            "decision": "REVISION_REQUIRED",
            "internship_member_id": ids[1],
        },
    )
    assert revision.status_code == 200
    assert client.get(url, headers=headers["mentor_a"]).json()["status"] == "REVISION_REQUIRED"
    assert client.delete(url + "/submission", headers=headers["intern_b"]).status_code == 204
    assert client.get(url, headers=headers["mentor_a"]).json()["status"] == "TODO"
    assert (
        client.post(
            url + "/submit", headers=headers["intern_b"], json={"content": "B final"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            url + "/review",
            headers=headers["mentor_a"],
            json={
                "decision": "COMPLETED",
                "internship_member_id": ids[1],
            },
        ).status_code
        == 200
    )
    final = client.get(url, headers=headers["mentor_a"]).json()
    assert final["status"] == "COMPLETED"
    assert {a["status"] for a in final["assignees"]} == {"COMPLETED"}


def test_invalid_assignment_mode_is_rejected(client, task_test_data):
    response = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(task_test_data["mentor_a"].id)},
        json={
            "title": "Wrong mode",
            "assignment_mode": "UNKNOWN",
            "internship_member_ids": [str(task_test_data["member_a"].id)],
        },
    )
    assert response.status_code == 422


def test_full_flow_assign_submit_review_complete(client, task_test_data):
    mentor_a = task_test_data["mentor_a"]
    intern_a = task_test_data["intern_a"]
    member_a = task_test_data["member_a"]

    task = _create_task(client, mentor_a, member_a.id)
    assert task["status"] == "TODO"

    # Intern thấy task của mình
    lst = client.get("/api/v1/tasks", headers={"X-User-Id": str(intern_a.id)})
    assert lst.status_code == 200
    assert any(t["id"] == task["id"] for t in lst.json())

    # Intern nộp bài
    sub = client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(intern_a.id)},
        json={"content": "Bài làm lần 1"},
    )
    assert sub.status_code == 200, sub.text
    assert sub.json()["content"] == "Bài làm lần 1"

    # Task chuyển SUBMITTED
    detail = client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(mentor_a.id)})
    assert detail.json()["status"] == "SUBMITTED"

    # Mentor yêu cầu làm lại
    rev = client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"decision": "REVISION_REQUIRED", "review_comment": "Thiếu unit test"},
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVISION_REQUIRED"

    # Intern nộp lại -> ghi đè bài nộp duy nhất, review cũ bị xóa
    sub2 = client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(intern_a.id)},
        json={"content": "Bài làm lần 2 đã bổ sung test"},
    )
    assert sub2.status_code == 200
    assert sub2.json()["content"] == "Bài làm lần 2 đã bổ sung test"
    assert sub2.json()["status"] == "SUBMITTED"
    assert sub2.json()["id"] == sub.json()["id"]

    # Mentor xác nhận hoàn thành
    done = client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"decision": "COMPLETED", "review_comment": "Đạt"},
    )
    assert done.json()["status"] == "ACCEPTED"
    detail2 = client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(intern_a.id)})
    assert detail2.json()["status"] == "COMPLETED"
    assert len(detail2.json()["submissions"]) == 1


def test_intern_can_delete_own_open_submission(client, task_test_data):
    mentor = task_test_data["mentor_a"]
    intern = task_test_data["intern_a"]
    member = task_test_data["member_a"]
    task = _create_task(client, mentor, member.id, title="Task delete submission")

    submitted = client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(intern.id)},
        json={"content": "Bài nộp sẽ xóa"},
    )
    assert submitted.status_code == 200

    deleted = client.delete(
        f"/api/v1/tasks/{task['id']}/submission",
        headers={"X-User-Id": str(intern.id)},
    )
    assert deleted.status_code == 204

    detail = client.get(
        f"/api/v1/tasks/{task['id']}",
        headers={"X-User-Id": str(intern.id)},
    )
    assert detail.status_code == 200
    assert detail.json()["submissions"] == []
    assert detail.json()["status"] == "TODO"


def test_task_status_contract_rejects_removed_in_progress_status(client, task_test_data):
    mentor = task_test_data["mentor_a"]
    member = task_test_data["member_a"]
    task = _create_task(client, mentor, member.id, title="Task status contract")

    response = client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers={"X-User-Id": str(mentor.id)},
        json={"status": "IN_PROGRESS"},
    )

    assert response.status_code == 422


def test_intern_cannot_delete_another_intern_submission(client, task_test_data):
    mentor = task_test_data["mentor_a"]
    owner = task_test_data["intern_a"]
    other_intern = task_test_data["intern_b"]
    member = task_test_data["member_a"]
    task = _create_task(client, mentor, member.id, title="Task protected submission")
    client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(owner.id)},
        json={"content": "Bài nộp của Intern A"},
    )

    deleted = client.delete(
        f"/api/v1/tasks/{task['id']}/submission",
        headers={"X-User-Id": str(other_intern.id)},
    )
    assert deleted.status_code == 403


def test_intern_cannot_delete_submission_after_task_completed(client, task_test_data):
    mentor = task_test_data["mentor_a"]
    intern = task_test_data["intern_a"]
    member = task_test_data["member_a"]
    task = _create_task(client, mentor, member.id, title="Task completed submission")
    client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(intern.id)},
        json={"content": "Bài nộp đã duyệt"},
    )
    client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers={"X-User-Id": str(mentor.id)},
        json={"decision": "COMPLETED"},
    )

    deleted = client.delete(
        f"/api/v1/tasks/{task['id']}/submission",
        headers={"X-User-Id": str(intern.id)},
    )
    assert deleted.status_code == 400

    detail = client.get(
        f"/api/v1/tasks/{task['id']}",
        headers={"X-User-Id": str(intern.id)},
    )
    assert len(detail.json()["submissions"]) == 1


def test_comment_exchange_both_sides(client, task_test_data):
    mentor_a = task_test_data["mentor_a"]
    intern_a = task_test_data["intern_a"]
    member_a = task_test_data["member_a"]
    task = _create_task(client, mentor_a, member_a.id, title="Task comment")

    c1 = client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        headers={"X-User-Id": str(intern_a.id)},
        json={"content": "Em hỏi về deadline ạ"},
    )
    assert c1.status_code == 200
    c2 = client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"content": "Cứ nộp trước thứ 6 nhé"},
    )
    assert c2.status_code == 200
    lst = client.get(
        f"/api/v1/tasks/{task['id']}/comments", headers={"X-User-Id": str(intern_a.id)}
    )
    assert len(lst.json()) == 2


def test_rbac_boundaries(client, task_test_data):
    mentor_a = task_test_data["mentor_a"]
    mentor_b = task_test_data["mentor_b"]
    intern_a = task_test_data["intern_a"]
    intern_b = task_test_data["intern_b"]
    member_a = task_test_data["member_a"]

    task = _create_task(client, mentor_a, member_a.id, title="Task RBAC")

    # Mentor B không xem được task của Mentor A
    r = client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(mentor_b.id)})
    assert r.status_code == 403

    # Intern B không xem được task của Intern A
    r2 = client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(intern_b.id)})
    assert r2.status_code == 403

    # Intern không được tự tạo task
    r3 = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(intern_a.id)},
        json={"internship_member_id": str(member_a.id), "title": "X"},
    )
    assert r3.status_code == 403

    # Intern không được tự hoàn thành (review)
    r4 = client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers={"X-User-Id": str(intern_a.id)},
        json={"decision": "COMPLETED"},
    )
    assert r4.status_code in (401, 403)

    # Mentor không được nộp bài hộ
    r5 = client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"content": "hoc ho"},
    )
    assert r5.status_code in (401, 403)

    # Submission rỗng bị từ chối
    r6 = client.post(
        f"/api/v1/tasks/{task['id']}/submit",
        headers={"X-User-Id": str(intern_a.id)},
        json={"content": "  "},
    )
    assert r6.status_code == 400


def test_admin_has_no_task_access(client, task_test_data):
    """UC-7: Admin không tham gia quản lý Task (403 mọi endpoint)."""
    admin = task_test_data["admin"]
    mentor_a = task_test_data["mentor_a"]
    member_a = task_test_data["member_a"]
    task = _create_task(client, mentor_a, member_a.id, title="Task no-admin")

    assert client.get("/api/v1/tasks", headers={"X-User-Id": str(admin.id)}).status_code == 403
    assert (
        client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(admin.id)}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/tasks",
            headers={"X-User-Id": str(admin.id)},
            json={"internship_member_id": str(member_a.id), "title": "Admin task"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/tasks/{task['id']}/review",
            headers={"X-User-Id": str(admin.id)},
            json={"decision": "COMPLETED"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/tasks/{task['id']}/comments", headers={"X-User-Id": str(admin.id)}
        ).status_code
        == 403
    )


def test_task_attachment_url_flow(client, task_test_data):
    """Mentor đính kèm 1 tệp (url_tep) khi giao task; Intern xem được."""
    mentor_a = task_test_data["mentor_a"]
    intern_a = task_test_data["intern_a"]
    member_a = task_test_data["member_a"]

    # Upload 1 file với quyền Mentor
    resp = client.post(
        "/api/v1/tasks/upload",
        headers={"X-User-Id": str(mentor_a.id)},
        files={"files": ("tai-lieu.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    file_url = resp.json()["urls"][0]

    # Tạo task kèm url_tep
    deadline = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    created = client.post(
        "/api/v1/tasks",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "internship_member_id": str(member_a.id),
            "title": "Task có tài liệu",
            "description": "Đọc tài liệu trước",
            "deadline": deadline,
            "priority": "MEDIUM",
            "attachment_url": file_url,
        },
    )
    assert created.status_code == 200, created.text
    task_id = created.json()["id"]
    assert created.json()["attachment_url"] == file_url

    # Intern xem được đính kèm trong chi tiết
    detail = client.get(f"/api/v1/tasks/{task_id}", headers={"X-User-Id": str(intern_a.id)})
    assert detail.status_code == 200
    assert detail.json()["attachment_url"] == file_url

    # URL ngoài hệ thống upload bị từ chối
    bad = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"attachment_url": "not-a-file-url"},
    )
    assert bad.status_code == 400

    # Mentor thay tệp khác rồi gỡ đính kèm
    up2 = client.post(
        "/api/v1/tasks/upload",
        headers={"X-User-Id": str(mentor_a.id)},
        files={"files": ("tai-lieu-2.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    file_url2 = up2.json()["urls"][0]
    updated = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"attachment_url": file_url2},
    )
    assert updated.json()["attachment_url"] == file_url2
    cleared = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"attachment_url": None},
    )
    assert cleared.json()["attachment_url"] is None


def test_filter_tasks_by_internship(client, task_test_data):
    """Lọc task theo đợt thực tập, vẫn giữ phạm vi Mentor/Intern."""
    mentor_a = task_test_data["mentor_a"]
    intern_a = task_test_data["intern_a"]
    member_a = task_test_data["member_a"]
    internship_id = member_a.internship_id

    # Đợt khác + member khác (cùng mentor/intern để đơn giản)
    factory = get_session_factory()
    session = factory()
    other_period = Internship(
        name=f"TOther {uuid.uuid4().hex[:6]}",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
        status=InternshipStatus.ONGOING,
        created_by=mentor_a.id,
    )
    session.add(other_period)
    session.commit()
    other_member = InternshipMember(
        internship_id=other_period.id,
        intern_id=intern_a.id,
        mentor_id=mentor_a.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add(other_member)
    session.commit()
    other_member_id = str(other_member.id)
    other_period_id = str(other_period.id)
    session.close()

    t1 = _create_task(client, mentor_a, member_a.id, title="Task dot A")
    t2 = _create_task(client, mentor_a, other_member_id, title="Task dot B")

    # Mentor lọc theo đợt A
    resp = client.get(
        f"/api/v1/tasks?internship_id={internship_id}",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert t1["id"] in ids
    assert t2["id"] not in ids

    # Intern lọc theo đợt B
    resp2 = client.get(
        f"/api/v1/tasks?internship_id={other_period_id}",
        headers={"X-User-Id": str(intern_a.id)},
    )
    assert resp2.status_code == 200
    ids2 = [t["id"] for t in resp2.json()]
    assert t2["id"] in ids2
    assert t1["id"] not in ids2


def test_task_search_by_intern_name_preserves_mentor_scope(client, task_test_data):
    mentor_a = task_test_data["mentor_a"]
    mentor_b = task_test_data["mentor_b"]
    member_a = task_test_data["member_a"]
    member_b = task_test_data["member_b"]
    own_task = _create_task(client, mentor_a, member_a.id, title="Backend cleanup")
    _create_task(client, mentor_b, member_b.id, title="Frontend cleanup")

    response = client.get(
        "/api/v1/tasks?search=intern",
        headers={"X-User-Id": str(mentor_a.id)},
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [own_task["id"]]


def test_task_lists_include_internship_name_for_mentor_and_intern(client, task_test_data):
    mentor = task_test_data["mentor_a"]
    intern = task_test_data["intern_a"]
    member = task_test_data["member_a"]
    internship = task_test_data["internship"]
    task = _create_task(client, mentor, member.id, title="Task shows internship")

    mentor_response = client.get(
        "/api/v1/tasks",
        headers={"X-User-Id": str(mentor.id)},
    )
    assert mentor_response.status_code == 200
    mentor_task = next(item for item in mentor_response.json() if item["id"] == task["id"])
    assert mentor_task["internship_name"] == internship.name

    intern_response = client.get(
        "/api/v1/tasks",
        headers={"X-User-Id": str(intern.id)},
    )
    assert intern_response.status_code == 200
    intern_task = next(item for item in intern_response.json() if item["id"] == task["id"])
    assert intern_task["internship_name"] == internship.name
