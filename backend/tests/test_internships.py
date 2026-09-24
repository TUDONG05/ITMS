import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import InternshipStatus, MemberStatus, UserRole, UserStatus
from app.models.internship import Internship
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
        email=f"admin_{suffix}@example.com",
        password_hash="hash",
        full_name="Admin Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    mentor = User(
        email=f"mentor_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Test",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    mentor_2 = User(
        email=f"mentor2_{suffix}@example.com",
        password_hash="hash",
        full_name="Mentor Two Test",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern = User(
        email=f"intern_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Test",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    intern_2 = User(
        email=f"intern2_{suffix}@example.com",
        password_hash="hash",
        full_name="Intern Two Test",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )

    session.add_all([admin, mentor, mentor_2, intern, intern_2])
    session.commit()
    for u in [admin, mentor, mentor_2, intern, intern_2]:
        session.refresh(u)

    users_map = {
        "admin": admin,
        "mentor": mentor,
        "mentor_2": mentor_2,
        "intern": intern,
        "intern_2": intern_2,
    }

    yield users_map

    cleanup_session = factory()
    try:
        created_internships = (
            cleanup_session.query(Internship).filter(Internship.created_by == admin.id).all()
        )
        for itn in created_internships:
            cleanup_session.delete(itn)
        cleanup_session.commit()

        for u in [admin, mentor, mentor_2, intern, intern_2]:
            user_to_delete = cleanup_session.get(User, u.id)
            if user_to_delete:
                cleanup_session.delete(user_to_delete)
        cleanup_session.commit()
    finally:
        cleanup_session.close()


def test_admin_create_internship(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Spring Batch {uuid.uuid4().hex[:6]}",
            "description": "Full-stack development internship",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == InternshipStatus.DRAFT
    assert data["created_by"] == str(admin.id)
    assert "id" in data


def test_admin_update_internship(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Initial Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-05-31",
        },
    )
    assert create_resp.status_code == 201
    internship_id = create_resp.json()["id"]

    new_name = f"Updated Batch {uuid.uuid4().hex[:6]}"
    update_resp = client.patch(
        f"/api/v1/internships/{internship_id}",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": new_name,
            "status": InternshipStatus.OPEN,
            "end_date": "2026-06-30",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == new_name
    assert data["status"] == InternshipStatus.OPEN
    assert data["end_date"] == "2026-06-30"


def test_mentor_cannot_create_internship(client: TestClient, test_data: dict[str, User]) -> None:
    mentor = test_data["mentor"]
    resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(mentor.id)},
        json={
            "name": f"Mentor Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]


def test_intern_cannot_create_internship(client: TestClient, test_data: dict[str, User]) -> None:
    intern = test_data["intern"]
    resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(intern.id)},
        json={
            "name": f"Intern Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]


def test_add_intern_to_internship(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]
    mentor = test_data["mentor"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Member Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    enroll_resp = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={
            "intern_id": str(intern.id),
            "mentor_id": str(mentor.id),
        },
    )
    assert enroll_resp.status_code == 201
    member = enroll_resp.json()
    assert member["intern_id"] == str(intern.id)
    assert member["mentor_id"] == str(mentor.id)
    assert member["status"] == MemberStatus.ACTIVE
    assert member["intern"]["full_name"] == intern.full_name
    assert member["mentor"]["full_name"] == mentor.full_name


def test_cannot_add_mentor_as_intern(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    mentor = test_data["mentor"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Invalid Intern Test {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    enroll_resp = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(mentor.id)},
    )
    assert enroll_resp.status_code == 400
    assert "does not have role INTERN" in enroll_resp.json()["detail"]


def test_cannot_add_duplicate_intern(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Duplicate Member Test {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    resp1 = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(intern.id)},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(intern.id)},
    )
    assert resp2.status_code == 409
    assert "already enrolled" in resp2.json()["detail"]


def test_assign_mentor_success(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]
    mentor = test_data["mentor"]
    mentor_2 = test_data["mentor_2"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Mentor Batch {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    enroll_resp = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(intern.id)},
    )
    assert enroll_resp.status_code == 201
    member_id = enroll_resp.json()["id"]
    assert enroll_resp.json()["mentor_id"] is None

    # Assign mentor
    assign_resp = client.patch(
        f"/api/v1/internship-members/{member_id}/mentor",
        headers={"X-User-Id": str(admin.id)},
        json={"mentor_id": str(mentor.id)},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["mentor_id"] == str(mentor.id)

    # Change mentor
    change_resp = client.patch(
        f"/api/v1/internship-members/{member_id}/mentor",
        headers={"X-User-Id": str(admin.id)},
        json={"mentor_id": str(mentor_2.id)},
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["mentor_id"] == str(mentor_2.id)


def test_cannot_assign_intern_as_mentor(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    intern = test_data["intern"]
    intern_2 = test_data["intern_2"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Invalid Mentor Test {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    enroll_resp = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(admin.id)},
        json={"intern_id": str(intern.id)},
    )
    member_id = enroll_resp.json()["id"]

    assign_resp = client.patch(
        f"/api/v1/internship-members/{member_id}/mentor",
        headers={"X-User-Id": str(admin.id)},
        json={"mentor_id": str(intern_2.id)},
    )
    assert assign_resp.status_code == 400
    assert "does not have role MENTOR" in assign_resp.json()["detail"]


def test_mentor_and_intern_cannot_perform_admin_actions(
    client: TestClient, test_data: dict[str, User]
) -> None:
    admin = test_data["admin"]
    mentor = test_data["mentor"]
    intern = test_data["intern"]

    create_resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Admin Lock Test {uuid.uuid4().hex[:6]}",
            "start_date": "2026-03-01",
            "end_date": "2026-06-30",
        },
    )
    internship_id = create_resp.json()["id"]

    # Mentor cannot enroll intern
    resp1 = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(mentor.id)},
        json={"intern_id": str(intern.id)},
    )
    assert resp1.status_code == 403

    # Intern cannot enroll intern
    resp2 = client.post(
        f"/api/v1/internships/{internship_id}/members",
        headers={"X-User-Id": str(intern.id)},
        json={"intern_id": str(intern.id)},
    )
    assert resp2.status_code == 403


def test_invalid_date_rejected(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    resp = client.post(
        "/api/v1/internships",
        headers={"X-User-Id": str(admin.id)},
        json={
            "name": f"Invalid Dates {uuid.uuid4().hex[:6]}",
            "start_date": "2026-06-01",
            "end_date": "2026-05-01",
        },
    )
    assert resp.status_code in (400, 422)


def test_internship_not_found(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    fake_id = uuid.uuid4()

    get_resp = client.get(
        f"/api/v1/internships/{fake_id}",
        headers={"X-User-Id": str(admin.id)},
    )
    assert get_resp.status_code == 404
    assert get_resp.json()["detail"] == "Internship not found"

    patch_resp = client.patch(
        f"/api/v1/internships/{fake_id}",
        headers={"X-User-Id": str(admin.id)},
        json={"name": "New Name"},
    )
    assert patch_resp.status_code == 404


def test_internship_member_not_found(client: TestClient, test_data: dict[str, User]) -> None:
    admin = test_data["admin"]
    mentor = test_data["mentor"]
    fake_member_id = uuid.uuid4()

    patch_resp = client.patch(
        f"/api/v1/internship-members/{fake_member_id}/mentor",
        headers={"X-User-Id": str(admin.id)},
        json={"mentor_id": str(mentor.id)},
    )
    assert patch_resp.status_code == 404
    assert patch_resp.json()["detail"] == "Internship member not found"
