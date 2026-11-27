import uuid
from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine, get_session_factory
from app.main import app
from app.models.internship import (
    Internship,
    InternshipApplication,
    InternshipMember,
    InternshipRequest,
    InternshipRoadmap,
)
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.user import User
from app.schemas.internship import InternshipApplicationCreate
from app.services.internship import InternshipService


@pytest.fixture
def delete_cohort_data():
    with get_session_factory()() as db:
        users = {
            role: User(
                email=f"delete-cohort-{uuid.uuid4().hex}@example.com",
                password_hash="hash",
                full_name=role,
                role=role,
                status="ACTIVE",
            )
            for role in ("ADMIN", "MENTOR", "INTERN")
        }
        roadmap = Roadmap(
            name=f"Retained curriculum {uuid.uuid4().hex}", status="ACTIVE", position="BACKEND"
        )
        cohort = Internship(
            name=f"Delete cohort {uuid.uuid4().hex}",
            status="OPEN",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add_all([*users.values(), roadmap, cohort])
        db.flush()
        phase = Phase(roadmap_id=roadmap.id, name="Retained phase", order_no=1)
        db.add(phase)
        db.flush()
        content = LearningContent(
            phase_id=phase.id, title="Retained content", type="LESSON", order_no=1
        )
        db.add_all(
            [
                content,
                InternshipRoadmap(
                    internship_id=cohort.id, position="BACKEND", roadmap_id=roadmap.id
                ),
            ]
        )
        db.commit()
        yield db, users, cohort, roadmap, phase, content


def h(users, role="ADMIN"):
    return {"X-User-Id": str(users[role].id)}


def test_admin_deletes_empty_cohort_but_retains_its_roadmap_and_materials(delete_cohort_data):
    db, users, cohort, roadmap, phase, content = delete_cohort_data
    cohort_id = cohort.id
    response = TestClient(app).delete(f"/api/v1/internships/{cohort_id}", headers=h(users))
    assert response.status_code == 204, response.text
    assert response.content == b""
    db.expire_all()
    assert db.get(Internship, cohort_id) is None
    assert (
        db.scalar(
            select(InternshipRoadmap.internship_id).where(
                InternshipRoadmap.internship_id == cohort_id
            )
        )
        is None
    )
    assert db.get(Roadmap, roadmap.id) is not None
    assert db.get(Phase, phase.id) is not None
    assert db.get(LearningContent, content.id) is not None


@pytest.mark.parametrize("member_status", ["ACTIVE", "EXTENDED", "STOPPED", "COMPLETED"])
def test_any_membership_status_blocks_deletion_and_preserves_history(
    delete_cohort_data, member_status
):
    db, users, cohort, roadmap, _, content = delete_cohort_data
    member = InternshipMember(
        internship_id=cohort.id,
        intern_id=users["INTERN"].id,
        mentor_id=users["MENTOR"].id,
        position="BACKEND",
        roadmap_id=roadmap.id,
        status=member_status,
    )
    db.add(member)
    db.flush()
    progress = LearningProgress(
        internship_member_id=member.id,
        content_id=content.id,
        status="COMPLETED",
        progress_percent=100,
    )
    history = InternshipRequest(
        internship_member_id=member.id,
        requested_by=users["MENTOR"].id,
        type="COMPLETE",
        reason="Completed history",
        status="APPROVED",
    )
    db.add_all([progress, history])
    db.commit()
    response = TestClient(app).delete(f"/api/v1/internships/{cohort.id}", headers=h(users))
    assert response.status_code == 409
    db.expire_all()
    assert db.get(InternshipMember, member.id).status == member_status
    assert db.get(LearningProgress, progress.id).progress_percent == 100
    assert db.get(InternshipRequest, history.id).reason == "Completed history"
    assert db.get(Internship, cohort.id) is not None


@pytest.mark.parametrize("application_status", ["PENDING", "APPROVED", "REJECTED"])
def test_applications_are_removed_when_deleting_a_cohort_without_members(
    delete_cohort_data, application_status
):
    db, users, cohort, _, _, _ = delete_cohort_data
    application = InternshipApplication(
        internship_id=cohort.id,
        intern_id=users["INTERN"].id,
        position="BACKEND",
        status=application_status,
    )
    db.add(application)
    db.commit()
    cohort_id, application_id = cohort.id, application.id
    response = TestClient(app).delete(f"/api/v1/internships/{cohort_id}", headers=h(users))
    assert response.status_code == 204
    db.expire_all()
    assert db.get(InternshipApplication, application_id) is None
    assert db.get(Internship, cohort_id) is None


def test_delete_requires_admin_and_returns_missing404(delete_cohort_data):
    db, users, cohort, _, _, _ = delete_cohort_data
    client = TestClient(app)
    url = f"/api/v1/internships/{cohort.id}"
    assert client.delete(url).status_code == 401
    for role in ("MENTOR", "INTERN"):
        assert client.delete(url, headers=h(users, role)).status_code == 403
    assert client.delete(f"/api/v1/internships/{uuid.uuid4()}", headers=h(users)).status_code == 404
    assert db.get(Internship, cohort.id) is not None


def test_registration_refreshes_stale_cohort_after_another_session_deletes_it():
    engine = get_engine()
    if "single_intern_test_" not in str(engine.url.query.get("options", "")):
        pytest.skip("Independent committed sessions require disposable-schema runner")
    with Session(engine, expire_on_commit=False) as first, Session(engine) as second:
        intern = User(
            email=f"stale-cohort-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Intern",
            role="INTERN",
            status="ACTIVE",
        )
        cohort = Internship(
            name=f"Stale cohort {uuid.uuid4().hex}",
            status="OPEN",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        first.add_all([intern, cohort])
        first.commit()
        cohort_id, intern_id = cohort.id, intern.id
        try:
            assert first.get(Internship, cohort_id).status == "OPEN"
            InternshipService.delete_internship(second, cohort_id)
            with pytest.raises(HTTPException) as missing:
                InternshipService.apply_internship(
                    first, cohort_id, intern_id, InternshipApplicationCreate(position="BACKEND")
                )
            assert missing.value.status_code == 404
            assert (
                first.scalar(
                    select(InternshipApplication.id).where(
                        InternshipApplication.intern_id == intern_id
                    )
                )
                is None
            )
        finally:
            first.rollback()
            second.rollback()
            remaining = first.get(Internship, cohort_id)
            if remaining is not None:
                first.delete(remaining)
            first.delete(first.get(User, intern_id))
            first.commit()
