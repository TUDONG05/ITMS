import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.main import app
from app.models.internship import Internship, InternshipApplication, InternshipMember
from app.models.user import User
from app.services.mentor import MentorService


@pytest.fixture
def position_data():
    with get_session_factory()() as db:
        users = {
            key: User(
                email=f"position-{key}-{uuid.uuid4().hex}@example.com",
                password_hash="hash",
                full_name=key,
                role=role,
                status="ACTIVE",
            )
            for key, role in (
                ("admin", "ADMIN"),
                ("mentor", "MENTOR"),
                ("other_mentor", "MENTOR"),
                ("intern", "INTERN"),
            )
        }
        batch = Internship(
            name=f"Position {uuid.uuid4().hex}",
            status="OPEN",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add_all([*users.values(), batch])
        db.flush()
        member = InternshipMember(
            internship_id=batch.id,
            intern_id=users["intern"].id,
            mentor_id=users["mentor"].id,
            status="ACTIVE",
        )
        db.commit()
        yield db, users, member


def _headers(user):
    return {"X-User-Id": str(user.id)}


def _apply(client, users, member, body):
    return client.post(
        f"/api/v1/internships/{member.internship_id}/apply",
        headers=_headers(users["intern"]),
        json=body,
    )


@pytest.mark.parametrize("position", ["BACKEND", "FRONTEND", "FULLSTACK", "AI", "BA", "OTHER"])
def test_intern_selects_position_and_approval_copies_it(position_data, position):
    db, users, member = position_data
    client = TestClient(app)
    response = _apply(client, users, member, {"position": position})
    assert response.status_code == 201, response.text
    application = response.json()
    assert application["position"] == position
    listed = client.get("/api/v1/internships/my-applications", headers=_headers(users["intern"]))
    assert listed.json()[0]["position"] == position
    reviewed = client.patch(
        f"/api/v1/internships/applications/{application['id']}/review",
        headers=_headers(users["admin"]),
        json={"status": "APPROVED"},
    )
    assert reviewed.status_code == 200, reviewed.text
    membership = db.scalar(
        select(InternshipMember).where(InternshipMember.intern_id == users["intern"].id)
    )
    assert membership.position == position
    membership.mentor_id = users["mentor"].id
    db.commit()
    mine = client.get("/api/v1/internships/my-memberships", headers=_headers(users["intern"]))
    assert mine.json()[0]["position"] == position
    roster = MentorService.get_mentor_interns(db, users["mentor"])
    assert next(item for item in roster if item.id == membership.id).position == position
    assert MentorService.get_intern_detail(db, membership.id, users["mentor"]).position == position


@pytest.mark.parametrize(
    "body", [{}, {"position": None}, {"position": "DEVELOPER"}, {"position": "backend"}]
)
def test_new_applications_require_valid_position(position_data, body):
    _, users, member = position_data
    assert _apply(TestClient(app), users, member, body).status_code == 422


def test_rejected_resubmission_updates_chosen_position(position_data):
    db, users, member = position_data
    client = TestClient(app)
    first = _apply(client, users, member, {"position": "BACKEND"}).json()
    assert (
        client.patch(
            f"/api/v1/internships/applications/{first['id']}/review",
            headers=_headers(users["admin"]),
            json={"status": "REJECTED"},
        ).status_code
        == 200
    )
    second = _apply(client, users, member, {"position": "AI"})
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]
    assert second.json()["position"] == "AI"
    assert second.json()["status"] == "PENDING"
    db.expire_all()
    assert db.get(InternshipApplication, uuid.UUID(first["id"])).position == "AI"


def test_batch_approval_copies_chosen_position(position_data):
    db, users, member = position_data
    client = TestClient(app)
    application = _apply(client, users, member, {"position": "FULLSTACK"}).json()
    response = client.post(
        "/api/v1/internships/applications/batch-review",
        headers=_headers(users["admin"]),
        json={"ids": [application["id"]], "status": "APPROVED"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["processed_count"] == 1
    membership = db.scalar(
        select(InternshipMember).where(InternshipMember.intern_id == users["intern"].id)
    )
    assert membership.position == "FULLSTACK"


def test_legacy_null_application_remains_readable_and_approvable(position_data):
    db, users, member = position_data
    legacy = InternshipApplication(
        internship_id=member.internship_id, intern_id=users["intern"].id, status="PENDING"
    )
    db.add(legacy)
    db.commit()
    client = TestClient(app)
    response = client.get("/api/v1/internships/my-applications", headers=_headers(users["intern"]))
    assert response.json()[0]["position"] is None
    result = client.patch(
        f"/api/v1/internships/applications/{legacy.id}/review",
        headers=_headers(users["admin"]),
        json={"status": "APPROVED"},
    )
    assert result.status_code == 200
    membership = db.scalar(
        select(InternshipMember).where(InternshipMember.intern_id == users["intern"].id)
    )
    assert membership.position is None


def test_admin_and_mentor_cannot_edit_chosen_position(position_data):
    db, users, member = position_data
    db.add(member)
    db.commit()
    client = TestClient(app)
    for actor in ("admin", "mentor", "other_mentor", "intern"):
        result = client.patch(
            f"/api/v1/internship-members/{member.id}/position",
            headers=_headers(users[actor]),
            json={"position": "AI"},
        )
        assert result.status_code == 404
    result = client.patch(
        f"/api/v1/internship-members/{member.id}",
        headers=_headers(users["admin"]),
        json={"position": "AI"},
    )
    assert result.status_code == 422
    db.refresh(member)
    assert member.position is None


def test_database_rejects_invalid_application_position(position_data):
    db, users, member = position_data
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            db.add(
                InternshipApplication(
                    internship_id=member.internship_id,
                    intern_id=users["intern"].id,
                    status="PENDING",
                    position="INVALID",
                )
            )
            db.flush()
    assert error.value.orig.diag.constraint_name == "ck_internship_applications_position"


def test_database_rejects_invalid_membership_position(position_data):
    db, _, member = position_data
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            member.position = "INVALID"
            db.add(member)
            db.flush()
    assert error.value.orig.diag.constraint_name == "ck_internship_members_position"
