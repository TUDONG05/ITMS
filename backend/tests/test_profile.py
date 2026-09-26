import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import InternshipMemberStatus, UserRole, UserStatus
from app.models.internship import Internship, InternshipMember
from app.models.user import User


@pytest.fixture
def test_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    Internship.__table__.create(bind=engine)
    InternshipMember.__table__.create(bind=engine)
    with Session(engine) as session:
        yield session
    InternshipMember.__table__.drop(bind=engine)
    Internship.__table__.drop(bind=engine)
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
    mentor_id = uuid.uuid4()
    intern_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    mentor = User(
        id=mentor_id,
        email="mentor@itms.local",
        password_hash=hash_password("Mentor@12345"),
        full_name="Nguyễn Mentor",
        phone="0901111222",
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
    )
    intern = User(
        id=intern_id,
        email="intern@itms.local",
        password_hash=hash_password("Intern@12345"),
        full_name="Trần Intern",
        phone="0903333444",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
    )
    admin = User(
        id=admin_id,
        email="admin@itms.local",
        password_hash=hash_password("Admin@12345"),
        full_name="Vũ Admin",
        phone="0905555666",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    test_db_session.add_all([mentor, intern, admin])
    test_db_session.commit()

    return {"mentor": mentor, "intern": intern, "admin": admin}


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_get_profile_returns_own_info_without_mentor(
    client: TestClient, seeded_users: dict[str, User]
):
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "intern@itms.local"
    assert data["full_name"] == "Trần Intern"
    assert data["phone"] == "0903333444"
    assert data["role"] == "INTERN"
    assert data["mentor"] is None


def test_get_profile_returns_mentor_info_when_assigned(
    client: TestClient, seeded_users: dict[str, User], test_db_session: Session
):
    intern = seeded_users["intern"]
    mentor = seeded_users["mentor"]

    # Tạo đợt thực tập và gán mentor cho intern
    internship_id = uuid.uuid4()
    from datetime import date

    internship = Internship(
        id=internship_id,
        name="Đợt 1 - 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        status="ONGOING",
    )
    test_db_session.add(internship)
    test_db_session.flush()

    member = InternshipMember(
        id=uuid.uuid4(),
        internship_id=internship_id,
        intern_id=intern.id,
        mentor_id=mentor.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    test_db_session.add(member)
    test_db_session.commit()

    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["mentor"] is not None
    assert data["mentor"]["id"] == str(mentor.id)
    assert data["mentor"]["full_name"] == "Nguyễn Mentor"
    assert data["mentor"]["email"] == "mentor@itms.local"


def test_update_profile_phone(client: TestClient, seeded_users: dict[str, User]):
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={"phone": "0988776655"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["phone"] == "0988776655"
    assert data["full_name"] == "Trần Intern"  # Tên không đổi


def test_non_admin_cannot_change_name(client: TestClient, seeded_users: dict[str, User]):
    """Intern cố đổi tên -> bị chặn 403."""
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={"full_name": "Tên Bị Hacker Sửa"},
    )
    assert update_res.status_code == 403
    assert update_res.json()["error"]["code"] == "FORBIDDEN"


def test_cannot_change_email_or_role(client: TestClient, seeded_users: dict[str, User]):
    """Gửi email và role trong payload -> bị bỏ qua, không thể đổi."""
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={
            "email": "hacked@itms.local",
            "role": "ADMIN",
            "phone": "0912345678",
        },
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["email"] == "intern@itms.local"
    assert data["role"] == "INTERN"
    assert data["phone"] == "0912345678"


def test_admin_can_update_own_name(client: TestClient, seeded_users: dict[str, User]):
    """Admin được phép đổi tên."""
    token = _login(client, "admin@itms.local", "Admin@12345")
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={"full_name": "Vũ Tổng Quản Trị", "phone": "0999888777"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["full_name"] == "Vũ Tổng Quản Trị"
    assert data["phone"] == "0999888777"

    # Admin gửi tên rỗng -> 422
    empty_res = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={"full_name": "   "},
    )
    assert empty_res.status_code == 422
    assert empty_res.json()["error"]["code"] == "INVALID_FULL_NAME"


def test_upload_avatar_success(client: TestClient, seeded_users: dict[str, User], tmp_path: Path):
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    files = {"file": ("avatar.png", fake_image, "image/png")}

    response = client.post("/api/v1/profile/avatar", headers=headers, files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] is not None
    assert "/avatars/" in data["avatar_url"]
    assert data["avatar_url"].endswith(".png")


def test_upload_avatar_rejects_invalid_type(client: TestClient, seeded_users: dict[str, User]):
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    fake_text = io.BytesIO(b"malicious script content")
    files = {"file": ("exploit.sh", fake_text, "text/plain")}

    response = client.post("/api/v1/profile/avatar", headers=headers, files=files)
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_avatar_rejects_oversized_file(client: TestClient, seeded_users: dict[str, User]):
    token = _login(client, "intern@itms.local", "Intern@12345")
    headers = {"Authorization": f"Bearer {token}"}

    # 2MB + 10 bytes
    large_image = io.BytesIO(b"\xff\xd8\xff" + b"x" * (2 * 1024 * 1024 + 10))
    files = {"file": ("large.jpg", large_image, "image/jpeg")}

    response = client.post("/api/v1/profile/avatar", headers=headers, files=files)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
