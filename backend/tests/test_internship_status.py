import uuid
from collections.abc import Generator
from datetime import date, timedelta

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
def uc13_test_data() -> Generator[dict[str, User | Internship | InternshipMember]]:
    factory = get_session_factory()
    session = factory()

    suffix = uuid.uuid4().hex[:8]

    # Create users
    admin = User(
        email=f"admin_{suffix}@example.com",
        password_hash="hash",
        full_name="Admin Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    mentor_a = User(
        email=f"mentor_a_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Alice",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_b = User(
        email=f"mentor_b_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Bob",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern_a = User(
        email=f"intern_a_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Alex",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_b = User(
        email=f"intern_b_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Ben",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )

    session.add_all([admin, mentor_a, mentor_b, intern_a, intern_b])
    session.commit()

    # Create Internship batch
    internship = Internship(
        name=f"Batch {suffix}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipStatus.ONGOING,
        created_by=admin.id,
    )
    session.add(internship)
    session.commit()

    # Member A: assigned to Mentor A
    member_a = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_a.id,
        mentor_id=mentor_a.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipMemberStatus.ACTIVE,
    )
    # Member B: assigned to Mentor B
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor_b.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
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
        "internship": internship,
        "member_a": member_a,
        "member_b": member_b,
    }

    yield data

    # Cleanup
    session.rollback()
    session.close()


def test_01_mentor_creates_extend_proposal_success(
    client: TestClient, uc13_test_data: dict
) -> None:
    """1. Mentor creates Extend proposal successfully (status PENDING)."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    new_end_date = str(member_a.end_date + timedelta(days=30))
    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "EXTEND",
            "reason": "Cần thêm thời gian hoàn thành dự án thực tế",
            "requested_end_date": new_end_date,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "EXTEND"
    assert data["status"] == "PENDING"
    assert data["requested_end_date"] == new_end_date
    assert data["requested_by"] == str(mentor_a.id)


def test_02_mentor_creates_terminate_proposal_success(
    client: TestClient, uc13_test_data: dict
) -> None:
    """2. Mentor creates Terminate/Stop proposal successfully."""
    mentor_b = uc13_test_data["mentor_b"]
    member_b = uc13_test_data["member_b"]

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_b.id)},
        json={
            "member_id": str(member_b.id),
            "type": "TERMINATE",
            "reason": "Intern vi phạm quy chế nhiều lần",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "STOP"
    assert data["status"] == "PENDING"
    assert data["requested_by"] == str(mentor_b.id)


def test_03_mentor_creates_complete_proposal_success(
    client: TestClient, uc13_test_data: dict
) -> None:
    """3. Mentor creates Complete proposal successfully."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "COMPLETE",
            "reason": "Đã hoàn thành xuất sắc tất cả task và roadmap",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "COMPLETE"
    assert data["status"] == "PENDING"


def test_04_proposal_has_status_pending(client: TestClient, uc13_test_data: dict) -> None:
    """4. Proposal always has status PENDING upon creation."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "COMPLETE",
            "reason": "Hoàn thành giai đoạn",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"
    assert resp.json()["reviewed_by"] is None
    assert resp.json()["reviewed_at"] is None


def test_05_mentor_correctly_assigned_can_create(client: TestClient, uc13_test_data: dict) -> None:
    """5. Mentor correctly assigned to intern can create proposal."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Dừng thực tập lý do cá nhân",
        },
    )
    assert resp.status_code == 201


def test_06_mentor_not_assigned_cannot_create(client: TestClient, uc13_test_data: dict) -> None:
    """6. Mentor NOT assigned to intern receives HTTP 403."""
    mentor_b = uc13_test_data["mentor_b"]
    member_a = uc13_test_data["member_a"]  # Member A is assigned to mentor_a

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_b.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Cố ý đề xuất cho intern người khác",
        },
    )
    assert resp.status_code == 403
    assert "không phụ trách" in resp.json()["detail"].lower()


def test_07_authenticated_user_used_no_spoofing(client: TestClient, uc13_test_data: dict) -> None:
    """7. Authenticated user ID is strictly used as requested_by."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Xác minh requester ID",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["requested_by"] == str(mentor_a.id)


def test_08_br10_second_pending_extend_proposal_blocked(
    client: TestClient, uc13_test_data: dict
) -> None:
    """8. BR-10: Second pending Extend proposal for the same intern is blocked (HTTP 400)."""
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    new_date_1 = str(member_a.end_date + timedelta(days=15))
    resp1 = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "EXTEND",
            "reason": "Gia hạn lần 1",
            "requested_end_date": new_date_1,
        },
    )
    assert resp1.status_code == 201

    # Second EXTEND while the first is still PENDING
    new_date_2 = str(member_a.end_date + timedelta(days=30))
    resp2 = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "EXTEND",
            "reason": "Gia hạn lần 2 trùng lặp",
            "requested_end_date": new_date_2,
        },
    )
    assert resp2.status_code == 400
    assert "đang chờ xử lý" in resp2.json()["detail"].lower()


def test_09_manager_views_pending_proposals(client: TestClient, uc13_test_data: dict) -> None:
    """9. Manager views pending proposals."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Dừng thực tập để kiểm tra danh sách",
        },
    )

    resp = client.get(
        "/api/v1/internships/requests?status=PENDING",
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert any(it["internship_member_id"] == str(member_a.id) for it in items)


def test_10_manager_approves_extend_proposal(client: TestClient, uc13_test_data: dict) -> None:
    """10. Manager approves Extend proposal -> updates InternshipMember status and end_date."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    new_end_date = str(member_a.end_date + timedelta(days=45))
    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "EXTEND",
            "reason": "Gia hạn thêm 45 ngày",
            "requested_end_date": new_end_date,
        },
    )
    req_id = create_resp.json()["id"]

    review_resp = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Đồng ý gia hạn"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "APPROVED"

    # Verify InternshipMember updated
    factory = get_session_factory()
    with factory() as session:
        updated_member = session.get(InternshipMember, member_a.id)
        assert updated_member.status == InternshipMemberStatus.EXTENDED
        assert str(updated_member.end_date) == new_end_date


def test_11_manager_approves_terminate_proposal(client: TestClient, uc13_test_data: dict) -> None:
    """11. Manager approves Terminate/Stop proposal -> updates member status to STOPPED."""
    admin = uc13_test_data["admin"]
    mentor_b = uc13_test_data["mentor_b"]
    member_b = uc13_test_data["member_b"]

    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_b.id)},
        json={
            "member_id": str(member_b.id),
            "type": "STOP",
            "reason": "Dừng thực tập do yêu cầu",
        },
    )
    req_id = create_resp.json()["id"]

    review_resp = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Chấp thuận dừng"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "APPROVED"

    factory = get_session_factory()
    with factory() as session:
        updated_member = session.get(InternshipMember, member_b.id)
        assert updated_member.status == InternshipMemberStatus.STOPPED


def test_12_manager_approves_complete_proposal(client: TestClient, uc13_test_data: dict) -> None:
    """12. Manager approves Complete proposal -> updates InternshipMember status to COMPLETED."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "COMPLETE",
            "reason": "Hoàn thành kỳ thực tập",
        },
    )
    req_id = create_resp.json()["id"]

    review_resp = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Chúc mừng hoàn thành"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "APPROVED"

    factory = get_session_factory()
    with factory() as session:
        updated_member = session.get(InternshipMember, member_a.id)
        assert updated_member.status == InternshipMemberStatus.COMPLETED


def test_13_manager_rejects_proposal(client: TestClient, uc13_test_data: dict) -> None:
    """13. Manager rejects proposal -> proposal REJECTED, InternshipMember unchanged."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    orig_end_date = member_a.end_date

    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "EXTEND",
            "reason": "Xin gia hạn nhưng không hợp lệ",
            "requested_end_date": str(orig_end_date + timedelta(days=20)),
        },
    )
    req_id = create_resp.json()["id"]

    review_resp = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "REJECTED", "review_note": "Từ chối gia hạn vì chưa đủ điều kiện"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "REJECTED"

    factory = get_session_factory()
    with factory() as session:
        updated_member = session.get(InternshipMember, member_a.id)
        # Status remains ACTIVE and end_date unchanged
        assert updated_member.status == InternshipMemberStatus.ACTIVE
        assert updated_member.end_date == orig_end_date


def test_14_status_history_correctly_reflects_events(
    client: TestClient, uc13_test_data: dict
) -> None:
    """14. Status history correctly reflects initial state and proposals."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    # Create proposal and approve it
    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "COMPLETE",
            "reason": "Đã làm tốt",
        },
    )
    req_id = create_resp.json()["id"]
    client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Duyệt kết thúc"},
    )

    history_resp = client.get(
        f"/api/v1/mentor/interns/{member_a.id}/status-history",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert isinstance(history, list)
    assert len(history) >= 2
    actions = [h["action"] for h in history]
    assert "INITIAL" in actions
    assert "COMPLETE" in actions


def test_15_status_history_shows_requester_and_reviewer(
    client: TestClient, uc13_test_data: dict
) -> None:
    """15. Status history correctly populates requester and reviewer names."""
    admin = uc13_test_data["admin"]
    mentor_a = uc13_test_data["mentor_a"]
    member_a = uc13_test_data["member_a"]

    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Lý do kiểm tra tên",
        },
    )
    req_id = create_resp.json()["id"]
    client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Đồng ý"},
    )

    history_resp = client.get(
        f"/api/v1/mentor/interns/{member_a.id}/status-history",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert history_resp.status_code == 200
    stop_item = next(h for h in history_resp.json() if h["action"] == "STOP")
    assert stop_item["requested_by_name"] == mentor_a.full_name
    assert stop_item["reviewed_by_name"] == admin.full_name


def test_16_unauthorized_user_cannot_review(client: TestClient, uc13_test_data: dict) -> None:
    """16. Unauthorized user (intern, mentor) cannot review proposal (HTTP 403)."""
    mentor_a = uc13_test_data["mentor_a"]
    intern_a = uc13_test_data["intern_a"]
    member_a = uc13_test_data["member_a"]

    create_resp = client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "COMPLETE",
            "reason": "Hoàn thành",
        },
    )
    req_id = create_resp.json()["id"]

    # Mentor tries to review
    mentor_review = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(mentor_a.id)},
        json={"status": "APPROVED"},
    )
    assert mentor_review.status_code == 403

    # Intern tries to review
    intern_review = client.patch(
        f"/api/v1/internships/requests/{req_id}/review",
        headers={"X-User-Id": str(intern_a.id)},
        json={"status": "APPROVED"},
    )
    assert intern_review.status_code == 403


def test_17_mentor_cannot_view_other_intern_status_history(
    client: TestClient, uc13_test_data: dict
) -> None:
    """17. Mentor cannot view status history of an intern assigned to another mentor (HTTP 403)."""
    mentor_b = uc13_test_data["mentor_b"]
    member_a = uc13_test_data["member_a"]  # Member A belongs to Mentor A

    resp = client.get(
        f"/api/v1/mentor/interns/{member_a.id}/status-history",
        headers={"X-User-Id": str(mentor_b.id)},
    )
    assert resp.status_code == 403
    assert "không có quyền" in resp.json()["detail"].lower()


def test_18_mentor_proposals_data_isolation(client: TestClient, uc13_test_data: dict) -> None:
    """18. Mentor listing proposals only sees proposals for their own interns or requests."""
    mentor_a = uc13_test_data["mentor_a"]
    mentor_b = uc13_test_data["mentor_b"]
    member_a = uc13_test_data["member_a"]
    member_b = uc13_test_data["member_b"]

    # Mentor A creates proposal for Member A
    client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
        json={
            "member_id": str(member_a.id),
            "type": "STOP",
            "reason": "Đề xuất của Mentor A",
        },
    )

    # Mentor B creates proposal for Member B
    client.post(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_b.id)},
        json={
            "member_id": str(member_b.id),
            "type": "STOP",
            "reason": "Đề xuất của Mentor B",
        },
    )

    # Mentor A lists proposals
    resp_a = client.get(
        "/api/v1/mentor/proposals",
        headers={"X-User-Id": str(mentor_a.id)},
    )
    assert resp_a.status_code == 200
    items_a = resp_a.json()
    assert all(it["internship_member_id"] == str(member_a.id) for it in items_a)
    assert not any(it["internship_member_id"] == str(member_b.id) for it in items_a)
