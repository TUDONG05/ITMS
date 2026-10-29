import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import UserRole, UserStatus
from app.models.internship import Internship, InternshipApplication, InternshipMember
from app.models.user import User


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def test_data() -> Generator[dict[str, User]]:
    factory = get_session_factory()
    session = factory()

    suffix = uuid.uuid4().hex[:8]
    admin = User(
        email=f"admin_app_{suffix}@example.com",
        password_hash="hash",
        full_name="Admin App Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    intern = User(
        email=f"intern_app_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern App One",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_2 = User(
        email=f"intern2_app_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern App Two",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    mentor = User(
        email=f"mentor_app_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor App Test",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )

    session.add_all([admin, intern, intern_2, mentor])
    session.commit()
    for u in [admin, intern, intern_2, mentor]:
        session.refresh(u)

    users_map = {
        "admin": admin,
        "intern": intern,
        "intern_2": intern_2,
        "mentor": mentor,
    }

    yield users_map

    cleanup_session = factory()
    try:
        # Delete created applications
        apps = (
            cleanup_session.query(InternshipApplication)
            .filter(InternshipApplication.intern_id.in_([intern.id, intern_2.id]))
            .all()
        )
        for a in apps:
            cleanup_session.delete(a)
        cleanup_session.commit()

        # Delete created members
        members = (
            cleanup_session.query(InternshipMember)
            .filter(InternshipMember.intern_id.in_([intern.id, intern_2.id]))
            .all()
        )
        for m in members:
            cleanup_session.delete(m)
        cleanup_session.commit()

        # Delete internships
        itns = cleanup_session.query(Internship).filter(Internship.created_by == admin.id).all()
        for itn in itns:
            cleanup_session.delete(itn)
        cleanup_session.commit()

        # Delete users
        for u in [admin, intern, intern_2, mentor]:
            user_to_delete = cleanup_session.get(User, u.id)
            if user_to_delete:
                cleanup_session.delete(user_to_delete)
        cleanup_session.commit()
    finally:
        cleanup_session.close()


def test_intern_apply_to_open_internship_success(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    # Admin tạo đợt thực tập OPEN
    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Open Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.json()["id"]

    # Intern nộp đơn đăng ký
    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Em mong muốn được học hỏi và cống hiến cho dự án."},
    )
    assert apply_resp.status_code == 201
    data = apply_resp.json()
    assert data["status"] == "PENDING"
    assert data["intern_id"] == str(intern.id)
    assert data["internship_id"] == batch_id
    assert "Em mong muốn" in data["reason"]


def test_intern_cannot_apply_to_draft_or_closed_internship(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    # Đợt DRAFT
    draft_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Draft Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "DRAFT",
        },
    )
    batch_id = draft_resp.json()["id"]

    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Xin gia nhập đợt draft"},
    )
    assert apply_resp.status_code == 400
    assert "OPEN" in apply_resp.json()["detail"]


def test_intern_cannot_apply_duplicate(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Dup Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    batch_id = create_resp.json()["id"]

    # Đăng ký lần 1
    resp1 = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Lần 1"},
    )
    assert resp1.status_code == 201

    # Đăng ký lần 2 -> 409
    resp2 = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Lần 2 trùng"},
    )
    assert resp2.status_code == 409
    assert "chờ duyệt" in resp2.json()["detail"]


def test_intern_cannot_apply_if_already_member(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Member Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    batch_id = create_resp.json()["id"]

    # Thêm member trực tiếp vào DB để giả lập intern đã là thành viên
    factory = get_session_factory()
    with factory() as session:
        session.add(
            InternshipMember(
                internship_id=uuid.UUID(batch_id),
                intern_id=intern.id,
                status="ACTIVE",
            )
        )
        session.commit()

    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Xin gia nhập lại"},
    )
    assert apply_resp.status_code == 409
    assert "thành viên" in apply_resp.json()["detail"]


def test_intern_view_own_applications_isolation(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]
    intern_2 = test_data["intern_2"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Isolation Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    batch_id = create_resp.json()["id"]

    # Intern 1 nộp đơn
    client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Đơn của Intern 1"},
    )

    # Intern 2 nộp đơn
    client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern_2.id)},
        json={"reason": "Đơn của Intern 2"},
    )

    # Intern 1 xem danh sách đơn của mình
    resp1 = client.get(
        "/api/v1/internships/my-applications",
        headers={"X-User-Id": str(intern.id)},
    )
    assert resp1.status_code == 200
    apps1 = resp1.json()
    assert all(a["intern_id"] == str(intern.id) for a in apps1)
    assert not any(a["intern_id"] == str(intern_2.id) for a in apps1)

    # Intern không được phép xem toàn bộ đơn hệ thống (chỉ Admin)
    forbidden_resp = client.get(
        "/api/v1/internships/applications",
        headers={"X-User-Id": str(intern.id)},
    )
    assert forbidden_resp.status_code == 403


def test_admin_approve_application_adds_member_and_inherits_roadmap(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    # Admin tạo roadmap
    roadmap_resp = client.post(
        "/api/v1/training/roadmaps",
        headers={"X-User-Id": str(admin.id)},
        json={"name": f"App Roadmap {uuid.uuid4().hex[:6]}", "status": "ACTIVE"},
    )
    roadmap_id = roadmap_resp.json()["id"]

    # Admin tạo đợt có gắn roadmap
    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Approval Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
            "roadmap_id": roadmap_id,
        },
    )
    batch_id = create_resp.json()["id"]

    # Intern nộp đơn
    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Mong muốn tham gia thực tập backend."},
    )
    app_id = apply_resp.json()["id"]

    # Admin phê duyệt đơn
    approve_resp = client.patch(
        f"/api/v1/internships/applications/{app_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED", "review_note": "Hồ sơ đạt yêu cầu."},
    )
    assert approve_resp.status_code == 200
    app_data = approve_resp.json()
    assert app_data["status"] == "APPROVED"
    assert app_data["reviewed_by"] == str(admin.id)
    assert app_data["review_note"] == "Hồ sơ đạt yêu cầu."

    # Kiểm tra Intern đã được thêm vào thành viên của đợt và kế thừa roadmap
    members_resp = client.get(
        f"/api/v1/internships/{batch_id}/members",
        headers={"X-User-Id": str(admin.id)},
    )
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert len(members) == 1
    assert members[0]["intern_id"] == str(intern.id)
    assert members[0]["roadmap_id"] == roadmap_id
    assert members[0]["status"] == "ACTIVE"


def test_admin_reject_application_does_not_add_member(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Reject Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    batch_id = create_resp.json()["id"]

    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Nộp đơn"},
    )
    app_id = apply_resp.json()["id"]

    # Admin từ chối
    reject_resp = client.patch(
        f"/api/v1/internships/applications/{app_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "REJECTED", "review_note": "Chưa đủ điều kiện tham gia."},
    )
    assert reject_resp.status_code == 200
    app_data = reject_resp.json()
    assert app_data["status"] == "REJECTED"
    assert app_data["review_note"] == "Chưa đủ điều kiện tham gia."

    # Không có thành viên nào trong đợt
    members_resp = client.get(
        f"/api/v1/internships/{batch_id}/members",
        headers={"X-User-Id": str(admin.id)},
    )
    assert members_resp.status_code == 200
    assert len(members_resp.json()) == 0


def test_cannot_review_already_processed_application(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Re-review Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    batch_id = create_resp.json()["id"]

    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"reason": "Test re-review"},
    )
    app_id = apply_resp.json()["id"]

    # Phê duyệt lần 1
    client.patch(
        f"/api/v1/internships/applications/{app_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED"},
    )

    # Phê duyệt lần 2 -> 400
    re_review = client.patch(
        f"/api/v1/internships/applications/{app_id}/review",
        headers={"X-User-Id": str(admin.id)},
        json={"status": "APPROVED"},
    )
    assert re_review.status_code == 400
    assert "đã được xử lý" in re_review.json()["detail"]


def test_direct_enrollment_endpoint_returns_403_forbidden(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Deprecated Direct Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        },
    )
    batch_id = create_resp.json()["id"]

    direct_resp = client.post(
        f"/api/v1/internships/{batch_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(intern.id)},
    )
    assert direct_resp.status_code == 403
    assert "bị loại bỏ" in direct_resp.json()["detail"]


def test_intern_apply_without_reason_success(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Optional Reason Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.json()["id"]

    # Intern nộp đơn đăng ký không cần nhập lý do hay nguyện vọng (empty json)
    apply_resp = client.post(
        f"/api/v1/internships/{batch_id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={},
    )
    assert apply_resp.status_code == 201
    data = apply_resp.json()
    assert data["status"] == "PENDING"
    assert data["intern_id"] == str(intern.id)
    assert data["internship_id"] == batch_id
    assert data["reason"] is None


def test_admin_batch_review_applications(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern_1 = test_data["intern"]
    intern_2 = test_data["intern_2"]

    # Tạo đợt OPEN
    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Batch Review Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.json()["id"]

    # 2 interns apply
    resp1 = client.post(
        f"/api/v1/internships/{batch_id}/apply", headers={"X-User-Id": str(intern_1.id)}, json={}
    )
    resp2 = client.post(
        f"/api/v1/internships/{batch_id}/apply", headers={"X-User-Id": str(intern_2.id)}, json={}
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]

    # Admin batch approve
    batch_resp = client.post(
        "/api/v1/internships/applications/batch-review",
        headers={"X-User-Id": str(admin.id)},
        json={"ids": [id1, id2], "status": "APPROVED", "review_note": "Batch Approved"},
    )
    assert batch_resp.status_code == 200
    assert batch_resp.json()["processed_count"] == 2

    # Verify both members exist
    members_resp = client.get(
        f"/api/v1/internships/{batch_id}/members", headers={"X-User-Id": str(admin.id)}
    )
    assert members_resp.status_code == 200
    member_intern_ids = [m["intern_id"] for m in members_resp.json()]
    assert str(intern_1.id) in member_intern_ids
    assert str(intern_2.id) in member_intern_ids


def test_admin_approve_all_applications(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern_1 = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Approve All Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
            "status": "OPEN",
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.json()["id"]

    # Intern apply
    client.post(
        f"/api/v1/internships/{batch_id}/apply", headers={"X-User-Id": str(intern_1.id)}, json={}
    )

    # Admin approve all
    resp = client.post(
        "/api/v1/internships/applications/approve-all", headers={"X-User-Id": str(admin.id)}
    )
    assert resp.status_code == 200
    assert resp.json()["processed_count"] >= 1
