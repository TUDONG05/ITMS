import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.internship import Internship, InternshipApplication, InternshipMember
from app.models.user import User


@pytest.fixture
def memberships(request):
    with get_session_factory()() as db:
        users = {
            role: User(
                email=f"my-{role}-{uuid.uuid4().hex}@example.com",
                password_hash="hash",
                full_name=role,
                role=role,
                status="ACTIVE",
            )
            for role in ("ADMIN", "MENTOR", "INTERN")
        }
        other = User(
            email=f"other-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Other",
            role="INTERN",
            status="ACTIVE",
        )
        db.add_all([*users.values(), other])
        db.flush()
        for member_status in (getattr(request, "param", "ACTIVE"),):
            batch = Internship(
                name=f"My {uuid.uuid4().hex}",
                status="ONGOING",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )
            db.add(batch)
            db.flush()
            db.add(
                InternshipMember(
                    internship_id=batch.id,
                    intern_id=users["INTERN"].id,
                    mentor_id=users["MENTOR"].id if member_status == "ACTIVE" else None,
                    status=member_status,
                    end_date=date(2027, 1, 31),
                )
            )
            db.add(InternshipMember(internship_id=batch.id, intern_id=other.id, status="ACTIVE"))
        unjoined = Internship(
            name=f"Unjoined {uuid.uuid4().hex}",
            status="OPEN",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add(unjoined)
        db.flush()
        db.add(
            InternshipApplication(
                internship_id=unjoined.id, intern_id=users["INTERN"].id, status="PENDING"
            )
        )
        db.commit()
        yield users, other


@pytest.mark.parametrize(
    "memberships", ["ACTIVE", "EXTENDED", "COMPLETED", "STOPPED"], indirect=True
)
def test_my_memberships_only_returns_own_enrollments_and_history(memberships, request):
    users, _ = memberships
    response = TestClient(app).get(
        "/api/v1/internships/my-memberships", headers={"X-User-Id": str(users["INTERN"].id)}
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    expected_status = request.node.callspec.params["memberships"]
    assert items[0]["status"] == expected_status
    assert all(item["intern_id"] == str(users["INTERN"].id) for item in items)
    assert all(item["internship"]["name"].startswith("My ") for item in items)
    if expected_status == "ACTIVE":
        assert items[0]["mentor"]["id"] == str(users["MENTOR"].id)
    assert items[0]["end_date"] == "2027-01-31"
    assert items[0]["internship"]["end_date"] == "2026-12-31"
    assert all(item["mentor"] is None for item in items if item["status"] != "ACTIVE")


def test_my_memberships_requires_intern_role(memberships):
    users, _ = memberships
    client = TestClient(app)
    assert client.get("/api/v1/internships/my-memberships").status_code == 401
    for role in ("ADMIN", "MENTOR"):
        assert (
            client.get(
                "/api/v1/internships/my-memberships", headers={"X-User-Id": str(users[role].id)}
            ).status_code
            == 403
        )


def test_my_memberships_empty_for_unenrolled_intern(memberships):
    with get_session_factory()() as db:
        intern = User(
            email=f"empty-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Empty",
            role="INTERN",
            status="ACTIVE",
        )
        db.add(intern)
        db.commit()
        response = TestClient(app).get(
            "/api/v1/internships/my-memberships", headers={"X-User-Id": str(intern.id)}
        )
        assert response.status_code == 200
        assert response.json() == []
