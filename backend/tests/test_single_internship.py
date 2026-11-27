import uuid
from datetime import date
from importlib import import_module
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.main import app as api_app
from app.models.internship import Internship, InternshipApplication, InternshipMember
from app.models.user import User
from app.schemas.internship import (
    BatchReviewPayload,
    InternshipApplicationCreate,
    InternshipApplicationReview,
)
from app.services.internship import InternshipService


@pytest.fixture
def single_internship_data():
    with get_session_factory()() as db:
        intern = User(
            email=f"single-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Intern",
            role="INTERN",
            status="ACTIVE",
        )
        admin = User(
            email=f"single-admin-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Admin",
            role="ADMIN",
            status="ACTIVE",
        )
        batches = [
            Internship(
                name=f"Single {uuid.uuid4().hex}",
                status="OPEN",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )
            for _ in range(2)
        ]
        db.add_all([intern, admin, *batches])
        db.commit()
        yield db, intern, admin, batches


@pytest.mark.parametrize("member_status", ["ACTIVE", "EXTENDED", "COMPLETED", "STOPPED"])
def test_any_previous_membership_blocks_applying_and_approval(
    single_internship_data, member_status
):
    db, intern, admin, batches = single_internship_data
    db.add(InternshipMember(internship_id=batches[0].id, intern_id=intern.id, status=member_status))
    application = InternshipApplication(
        internship_id=batches[1].id, intern_id=intern.id, status="PENDING"
    )
    db.add(application)
    db.commit()
    with pytest.raises(HTTPException) as application_error:
        InternshipService.apply_internship(
            db, batches[1].id, intern.id, InternshipApplicationCreate(position="BACKEND")
        )
    assert application_error.value.status_code == 409
    with pytest.raises(HTTPException) as approval_error:
        InternshipService.review_application(
            db, application.id, InternshipApplicationReview(status="APPROVED"), admin.id
        )
    assert approval_error.value.status_code == 409
    db.refresh(application)
    assert application.status == "PENDING"
    assert (
        db.scalar(
            select(func.count())
            .select_from(InternshipMember)
            .where(InternshipMember.intern_id == intern.id)
        )
        == 1
    )


def test_batch_approves_only_one_of_multiple_pending_applications(single_internship_data):
    db, intern, admin, batches = single_internship_data
    applications = [
        InternshipApplication(internship_id=batch.id, intern_id=intern.id, status="PENDING")
        for batch in batches
    ]
    db.add_all(applications)
    db.commit()
    result = InternshipService.batch_review_applications(
        db, BatchReviewPayload(ids=[app.id for app in applications], status="APPROVED"), admin.id
    )
    assert result.processed_count == 1
    assert "1" in result.message
    for app in applications:
        db.refresh(app)
    assert [app.status for app in applications] == ["APPROVED", "PENDING"]
    members = list(
        db.scalars(select(InternshipMember).where(InternshipMember.intern_id == intern.id))
    )
    assert len(members) == 1
    assert members[0].internship_id == batches[0].id


@pytest.mark.parametrize("application_status", ["PENDING", "APPROVED"])
@pytest.mark.parametrize("same_batch", [True, False])
def test_pending_or_approved_application_blocks_another_registration(
    single_internship_data, application_status, same_batch
):
    db, intern, _, batches = single_internship_data
    original = InternshipApplication(
        internship_id=batches[0].id,
        intern_id=intern.id,
        status=application_status,
        position="BACKEND",
    )
    db.add(original)
    db.commit()
    target = batches[0] if same_batch else batches[1]
    response = TestClient(api_app).post(
        f"/api/v1/internships/{target.id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"position": "AI"},
    )
    assert response.status_code == 409
    applications = list(
        db.scalars(
            select(InternshipApplication).where(InternshipApplication.intern_id == intern.id)
        )
    )
    assert len(applications) == 1
    db.refresh(original)
    assert original.status == application_status
    assert original.position == "BACKEND"


@pytest.mark.parametrize("same_batch", [True, False])
def test_rejected_application_allows_registration_when_no_other_blocking_application(
    single_internship_data, same_batch
):
    db, intern, _, batches = single_internship_data
    rejected = InternshipApplication(
        internship_id=batches[0].id, intern_id=intern.id, status="REJECTED", position="BACKEND"
    )
    db.add(rejected)
    db.commit()
    target = batches[0] if same_batch else batches[1]
    response = TestClient(api_app).post(
        f"/api/v1/internships/{target.id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"position": "AI"},
    )
    assert response.status_code == 201
    assert response.json()["position"] == "AI"
    assert response.json()["status"] == "PENDING"
    if same_batch:
        assert response.json()["id"] == str(rejected.id)


def test_rejected_resubmission_is_blocked_by_another_pending_application(single_internship_data):
    db, intern, _, batches = single_internship_data
    rejected = InternshipApplication(
        internship_id=batches[0].id, intern_id=intern.id, status="REJECTED", position="BACKEND"
    )
    # Legacy multiple applications can still exist; don't allow reviving another one.
    db.add_all(
        [
            rejected,
            InternshipApplication(
                internship_id=batches[1].id, intern_id=intern.id, status="PENDING", position="AI"
            ),
        ]
    )
    db.commit()
    response = TestClient(api_app).post(
        f"/api/v1/internships/{batches[0].id}/apply",
        headers={"X-User-Id": str(intern.id)},
        json={"position": "BA"},
    )
    assert response.status_code == 409
    db.refresh(rejected)
    assert rejected.status == "REJECTED"
    assert rejected.position == "BACKEND"


def test_database_prevents_direct_second_membership(single_internship_data):
    db, intern, _, batches = single_internship_data
    db.add(InternshipMember(internship_id=batches[0].id, intern_id=intern.id, status="COMPLETED"))
    db.commit()
    with pytest.raises(IntegrityError) as exc:
        with db.begin_nested():
            db.add(
                InternshipMember(internship_id=batches[1].id, intern_id=intern.id, status="ACTIVE")
            )
            db.flush()
    assert exc.value.orig.diag.constraint_name == "uq_internship_members_single_intern"


def test_approval_translates_unique_constraint_race_to_conflict(
    single_internship_data, monkeypatch
):
    db, intern, admin, batches = single_internship_data
    db.add(InternshipMember(internship_id=batches[0].id, intern_id=intern.id, status="ACTIVE"))
    application = InternshipApplication(
        internship_id=batches[1].id, intern_id=intern.id, status="PENDING"
    )
    db.add(application)
    db.commit()
    # Simulate an external writer winning the race after the application-level check.
    monkeypatch.setattr(InternshipService, "_has_membership", staticmethod(lambda *_: False))
    with pytest.raises(HTTPException) as exc:
        InternshipService.review_application(
            db, application.id, InternshipApplicationReview(status="APPROVED"), admin.id
        )
    assert exc.value.status_code == 409
    db.refresh(application)
    assert application.status == "PENDING"


def test_batch_skips_unique_constraint_conflict_without_marking_approved(
    single_internship_data, monkeypatch
):
    db, intern, admin, batches = single_internship_data
    db.add(InternshipMember(internship_id=batches[0].id, intern_id=intern.id, status="STOPPED"))
    application = InternshipApplication(
        internship_id=batches[1].id, intern_id=intern.id, status="PENDING"
    )
    db.add(application)
    db.commit()
    monkeypatch.setattr(InternshipService, "_has_membership", staticmethod(lambda *_: False))
    result = InternshipService.batch_review_applications(
        db, BatchReviewPayload(ids=[application.id], status="APPROVED"), admin.id
    )
    assert result.processed_count == 0
    db.refresh(application)
    assert application.status == "PENDING"


def test_migration_refuses_duplicate_memberships_without_deleting_data(monkeypatch):
    migration = import_module("migrations.versions.0014_single_internship_per_intern")
    statements = []

    def execute(statement):
        statements.append(str(statement))
        return SimpleNamespace(scalar_one=lambda: 2)

    monkeypatch.setattr(migration.op, "get_bind", lambda: SimpleNamespace(execute=execute))
    monkeypatch.setattr(
        migration.op,
        "create_unique_constraint",
        lambda *_args, **_kwargs: pytest.fail("Constraint must not be created"),
    )
    with pytest.raises(RuntimeError, match="2 interns have multiple memberships"):
        migration.upgrade()
    assert len(statements) == 1
    assert statements[0].startswith("SELECT count(*)")
