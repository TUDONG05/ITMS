import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole, UserStatus
from app.models.user import User


@pytest.fixture
def test_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    with Session(engine) as session:
        yield session
    User.__table__.drop(bind=engine)
    engine.dispose()


@pytest.fixture
def client(test_db_session: Session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_users(test_db_session: Session):
    admin_id = uuid.uuid4()
    intern_id = uuid.uuid4()
    mentor_id = uuid.uuid4()

    admin = User(
        id=admin_id,
        email="admin@itms.local",
        password_hash=hash_password("Admin@12345"),
        full_name="Quản trị viên",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    intern = User(
        id=intern_id,
        email="intern@itms.local",
        password_hash=hash_password("Intern@12345"),
        full_name="Nguyễn Văn An",
        role=UserRole.INTERN.value,
        status=UserStatus.ACTIVE.value,
    )
    mentor = User(
        id=mentor_id,
        email="mentor@itms.local",
        password_hash=hash_password("Mentor@12345"),
        full_name="Trần Văn Bình",
        role=UserRole.MENTOR.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add_all([admin, intern, mentor])
    test_db_session.commit()
    return {"admin": admin, "intern": intern, "mentor": mentor}


def test_list_users(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    resp = client.get("/api/v1/users", headers={"X-User-Id": str(admin.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3

    # Filter by role
    resp_interns = client.get("/api/v1/users?role=INTERN", headers={"X-User-Id": str(admin.id)})
    assert resp_interns.status_code == 200
    assert len(resp_interns.json()) == 1
    assert resp_interns.json()[0]["email"] == "intern@itms.local"

    # Search by keyword
    resp_search = client.get("/api/v1/users?search=Nguyễn", headers={"X-User-Id": str(admin.id)})
    assert resp_search.status_code == 200
    assert len(resp_search.json()) == 1
    assert resp_search.json()[0]["full_name"] == "Nguyễn Văn An"


def test_create_user_success_by_admin(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    payload = {
        "email": "newintern@itms.local",
        "full_name": "Lê Thị Cúc",
        "password": "Password@123",
        "role": "INTERN",
        "status": "ACTIVE",
        "phone": "0987654321",
    }
    resp = client.post(
        "/api/v1/users",
        json=payload,
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newintern@itms.local"
    assert data["full_name"] == "Lê Thị Cúc"
    assert data["role"] == "INTERN"
    assert data["status"] == "ACTIVE"
    assert data["phone"] == "0987654321"


def test_create_user_forbidden_for_non_admin(client: TestClient, seeded_users):
    intern = seeded_users["intern"]
    payload = {
        "email": "hacker@itms.local",
        "full_name": "Hacker",
        "password": "Password@123",
        "role": "ADMIN",
    }
    resp = client.post(
        "/api/v1/users",
        json=payload,
        headers={"X-User-Id": str(intern.id)},
    )
    assert resp.status_code == 403


def test_create_user_duplicate_email(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    payload = {
        "email": "intern@itms.local",
        "full_name": "Trùng Email",
        "password": "Password@123",
        "role": "INTERN",
    }
    resp = client.post(
        "/api/v1/users",
        json=payload,
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 400
    assert "đã được sử dụng" in resp.json()["detail"]


def test_update_user_by_admin(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    intern = seeded_users["intern"]

    payload = {
        "full_name": "Nguyễn Văn An (Đã đổi tên)",
        "phone": "0123456789",
        "role": "MENTOR",
    }
    resp = client.patch(
        f"/api/v1/users/{intern.id}",
        json=payload,
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Nguyễn Văn An (Đã đổi tên)"
    assert data["phone"] == "0123456789"
    assert data["role"] == "MENTOR"


def test_lock_user_by_admin_and_prevent_login(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    intern = seeded_users["intern"]

    # Lock intern
    resp = client.patch(
        f"/api/v1/users/{intern.id}/status",
        json={"status": "LOCKED"},
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "LOCKED"

    # Attempt login with locked account
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "intern@itms.local", "password": "Intern@12345"},
    )
    assert login_resp.status_code == 403
    assert login_resp.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_cannot_self_lock(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    resp = client.patch(
        f"/api/v1/users/{admin.id}/status",
        json={"status": "LOCKED"},
        headers={"X-User-Id": str(admin.id)},
    )
    assert resp.status_code == 400
    assert "Không thể tự khóa" in resp.json()["detail"]


def test_unlock_user_and_can_login(client: TestClient, seeded_users):
    admin = seeded_users["admin"]
    intern = seeded_users["intern"]

    # Lock then unlock
    client.patch(
        f"/api/v1/users/{intern.id}/status",
        json={"status": "LOCKED"},
        headers={"X-User-Id": str(admin.id)},
    )
    unlock_resp = client.patch(
        f"/api/v1/users/{intern.id}/status",
        json={"status": "ACTIVE"},
        headers={"X-User-Id": str(admin.id)},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["status"] == "ACTIVE"

    # Now login succeeds
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "intern@itms.local", "password": "Intern@12345"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
