import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.models.internship import Internship, InternshipMember
from app.models.user import User


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def task_test_data() -> Generator[dict]:
    factory = get_session_factory()
    session = factory()
    suffix = uuid.uuid4().hex[:8]

    admin = User(email=f"t_admin_{suffix}@ex.com", password_hash="h", full_name="Admin T",
                 role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    mentor_a = User(email=f"t_ma_{suffix}@ex.com", password_hash="h", full_name="Mentor A",
                    role=UserRole.MENTOR, status=UserStatus.ACTIVE)
    mentor_b = User(email=f"t_mb_{suffix}@ex.com", password_hash="h", full_name="Mentor B",
                    role=UserRole.MENTOR, status=UserStatus.ACTIVE)
    intern_a = User(email=f"t_ia_{suffix}@ex.com", password_hash="h", full_name="Intern A",
                    role=UserRole.INTERN, status=UserStatus.ACTIVE)
    intern_b = User(email=f"t_ib_{suffix}@ex.com", password_hash="h", full_name="Intern B",
                    role=UserRole.INTERN, status=UserStatus.ACTIVE)
    session.add_all([admin, mentor_a, mentor_b, intern_a, intern_b])
    session.commit()

    internship = Internship(name=f"TBatch {suffix}", start_date=date(2026, 6, 1),
                            end_date=date(2026, 8, 31), status=InternshipStatus.ONGOING,
                            created_by=admin.id)
    session.add(internship)
    session.commit()

    member_a = InternshipMember(internship_id=internship.id, intern_id=intern_a.id,
                                mentor_id=mentor_a.id, status=InternshipMemberStatus.ACTIVE)
    member_b = InternshipMember(internship_id=internship.id, intern_id=intern_b.id,
                                mentor_id=mentor_b.id, status=InternshipMemberStatus.ACTIVE)
    session.add_all([member_a, member_b])
    session.commit()
    data = {"admin": admin, "mentor_a": mentor_a, "mentor_b": mentor_b,
            "intern_a": intern_a, "intern_b": intern_b,
            "member_a": member_a, "member_b": member_b,
            "internship": internship}
    yield data
    session.rollback()
    session.close()


def _create_task(client, mentor, member_id, title="Task 1"):
    deadline = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    resp = client.post("/api/v1/tasks", headers={"X-User-Id": str(mentor.id)},
                       json={"internship_member_id": str(member_id), "title": title,
                             "description": "Mô tả task", "deadline": deadline, "priority": "HIGH"})
    assert resp.status_code == 200, resp.text
    return resp.json()


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
    sub = client.post(f"/api/v1/tasks/{task['id']}/submit",
                      headers={"X-User-Id": str(intern_a.id)},
                      json={"content": "Bài làm lần 1"})
    assert sub.status_code == 200, sub.text
    assert sub.json()["content"] == "Bài làm lần 1"

    # Task chuyển SUBMITTED
    detail = client.get(f"/api/v1/tasks/{task['id']}", headers={"X-User-Id": str(mentor_a.id)})
    assert detail.json()["status"] == "SUBMITTED"

    # Mentor yêu cầu làm lại
    rev = client.post(f"/api/v1/tasks/{task['id']}/review",
                      headers={"X-User-Id": str(mentor_a.id)},
                      json={"decision": "REVISION_REQUIRED", "review_comment": "Thiếu unit test"})
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVISION_REQUIRED"

    # Intern nộp lại -> ghi đè bài nộp duy nhất, review cũ bị xóa
    sub2 = client.post(f"/api/v1/tasks/{task['id']}/submit",
                       headers={"X-User-Id": str(intern_a.id)},
                       json={"content": "Bài làm lần 2 đã bổ sung test"})
    assert sub2.status_code == 200
    assert sub2.json()["content"] == "Bài làm lần 2 đã bổ sung test"
    assert sub2.json()["status"] == "SUBMITTED"
    assert sub2.json()["id"] == sub.json()["id"]

    # Mentor xác nhận hoàn thành
    done = client.post(f"/api/v1/tasks/{task['id']}/review",
                       headers={"X-User-Id": str(mentor_a.id)},
                       json={"decision": "COMPLETED", "review_comment": "Đạt"})
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
    lst = client.get(f"/api/v1/tasks/{task['id']}/comments",
                     headers={"X-User-Id": str(intern_a.id)})
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
    r3 = client.post("/api/v1/tasks", headers={"X-User-Id": str(intern_a.id)},
                     json={"internship_member_id": str(member_a.id), "title": "X"})
    assert r3.status_code == 403

    # Intern không được tự hoàn thành (review)
    r4 = client.post(f"/api/v1/tasks/{task['id']}/review",
                     headers={"X-User-Id": str(intern_a.id)},
                     json={"decision": "COMPLETED"})
    assert r4.status_code in (401, 403)

    # Mentor không được nộp bài hộ
    r5 = client.post(f"/api/v1/tasks/{task['id']}/submit",
                     headers={"X-User-Id": str(mentor_a.id)}, json={"content": "hoc ho"})
    assert r5.status_code in (401, 403)

    # Submission rỗng bị từ chối
    r6 = client.post(f"/api/v1/tasks/{task['id']}/submit",
                     headers={"X-User-Id": str(intern_a.id)}, json={"content": "  "})
    assert r6.status_code == 400


def test_admin_has_no_task_access(client, task_test_data):
    """UC-7: Admin không tham gia quản lý Task (403 mọi endpoint)."""
    admin = task_test_data["admin"]
    mentor_a = task_test_data["mentor_a"]
    member_a = task_test_data["member_a"]
    task = _create_task(client, mentor_a, member_a.id, title="Task no-admin")

    assert client.get("/api/v1/tasks", headers={"X-User-Id": str(admin.id)}).status_code == 403
    assert client.get(f"/api/v1/tasks/{task['id']}",
                      headers={"X-User-Id": str(admin.id)}).status_code == 403
    assert client.post("/api/v1/tasks", headers={"X-User-Id": str(admin.id)},
                       json={"internship_member_id": str(member_a.id),
                             "title": "Admin task"}).status_code == 403
    assert client.post(f"/api/v1/tasks/{task['id']}/review",
                       headers={"X-User-Id": str(admin.id)},
                       json={"decision": "COMPLETED"}).status_code == 403
    assert client.get(f"/api/v1/tasks/{task['id']}/comments",
                      headers={"X-User-Id": str(admin.id)}).status_code == 403


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
