import uuid
from datetime import date
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.main import app
from app.models.internship import (
    Internship,
    InternshipApplication,
    InternshipMember,
    InternshipRoadmap,
)
from app.models.roadmap import LearningContent, LearningProgress, Phase, Roadmap
from app.models.user import User
from app.schemas.internship import (
    BatchReviewPayload,
    InternshipApplicationReview,
    InternshipMemberUpdate,
    InternshipUpdate,
)
from app.services.internship import InternshipService
from app.services.learning import LearningService


@pytest.fixture
def position_curricula():
    with get_session_factory()() as db:
        admin = User(
            email=f"position-admin-{uuid.uuid4().hex}@example.com",
            password_hash="hash",
            full_name="Admin",
            role="ADMIN",
            status="ACTIVE",
        )
        interns = {
            position: User(
                email=f"position-{uuid.uuid4().hex}@example.com",
                password_hash="hash",
                full_name=position,
                role="INTERN",
                status="ACTIVE",
            )
            for position in ("BACKEND", "FULLSTACK", "AI")
        }
        roadmaps = {
            position: Roadmap(
                name=f"{position} curriculum {uuid.uuid4().hex}", position=position, status="ACTIVE"
            )
            for position in ("BACKEND", "FULLSTACK")
        }
        cohort = Internship(
            name=f"Position cohort {uuid.uuid4().hex}",
            status="OPEN",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add_all([admin, *interns.values(), *roadmaps.values(), cohort])
        db.flush()
        for position, roadmap in roadmaps.items():
            db.add(
                InternshipRoadmap(internship_id=cohort.id, position=position, roadmap_id=roadmap.id)
            )
        applications = {
            position: InternshipApplication(
                internship_id=cohort.id, intern_id=intern.id, position=position, status="PENDING"
            )
            for position, intern in interns.items()
        }
        db.add_all(applications.values())
        db.commit()
        yield db, admin, interns, roadmaps, cohort, applications


def headers(user):
    return {"X-User-Id": str(user.id)}


def test_roadmap_creation_requires_position_and_reads_expose_it(position_curricula):
    _, admin, _, _, _, _ = position_curricula
    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/training/roadmaps", headers=headers(admin), json={"name": "Missing"}
        ).status_code
        == 422
    )
    created = client.post(
        "/api/v1/training/roadmaps",
        headers=headers(admin),
        json={"name": f"Frontend {uuid.uuid4().hex}", "position": "FRONTEND", "status": "ACTIVE"},
    )
    assert created.status_code == 201
    document = created.json()
    assert document["position"] == "FRONTEND"
    assert (
        client.get(f"/api/v1/training/roadmaps/{document['id']}", headers=headers(admin)).json()[
            "position"
        ]
        == "FRONTEND"
    )
    assert (
        client.patch(
            f"/api/v1/training/roadmaps/{document['id']}",
            headers=headers(admin),
            json={"position": None},
        ).status_code
        == 422
    )


def test_approval_and_bulk_select_matching_curriculum(position_curricula):
    db, admin, interns, roadmaps, _, applications = position_curricula
    result = InternshipService.batch_review_applications(
        db,
        BatchReviewPayload(
            ids=[applications[position].id for position in ("BACKEND", "FULLSTACK")],
            status="APPROVED",
        ),
        admin.id,
    )
    assert result.processed_count == 2
    for position in ("BACKEND", "FULLSTACK"):
        member = db.scalar(
            select(InternshipMember).where(InternshipMember.intern_id == interns[position].id)
        )
        assert member.roadmap_id == roadmaps[position].id
        assert LearningService.validate_member_roadmap(db, member).id == roadmaps[position].id


@pytest.mark.parametrize("position", [None, "AI"])
def test_single_approval_missing_position_or_mapping_is_atomic(position_curricula, position):
    db, admin, _, _, _, applications = position_curricula
    application = applications["AI"]
    application.position = position
    db.commit()
    with pytest.raises(HTTPException) as error:
        InternshipService.review_application(
            db, application.id, InternshipApplicationReview(status="APPROVED"), admin.id
        )
    assert error.value.status_code == 409
    db.refresh(application)
    assert application.status == "PENDING"
    assert (
        db.scalar(
            select(InternshipMember.id).where(InternshipMember.intern_id == application.intern_id)
        )
        is None
    )


def test_bulk_preflight_prevents_partial_enrollment(position_curricula):
    db, admin, _, _, _, applications = position_curricula
    with pytest.raises(HTTPException) as error:
        InternshipService.batch_review_applications(
            db,
            BatchReviewPayload(
                ids=[applications["BACKEND"].id, applications["AI"].id], status="APPROVED"
            ),
            admin.id,
        )
    assert error.value.status_code == 409
    for position in ("BACKEND", "AI"):
        db.refresh(applications[position])
        assert applications[position].status == "PENDING"
        assert (
            db.scalar(
                select(InternshipMember.id).where(
                    InternshipMember.intern_id == applications[position].intern_id
                )
            )
            is None
        )


def test_config_rejects_duplicate_positions_and_untyped_curricula(position_curricula):
    db, admin, _, roadmaps, cohort, _ = position_curricula
    duplicate = Roadmap(name=f"Duplicate {uuid.uuid4().hex}", position="BACKEND", status="ACTIVE")
    legacy = Roadmap(name=f"Untyped {uuid.uuid4().hex}", status="ACTIVE")
    db.add_all([duplicate, legacy])
    db.commit()
    client = TestClient(app)
    for ids in ([roadmaps["BACKEND"].id, duplicate.id], [legacy.id]):
        response = client.patch(
            f"/api/v1/internships/{cohort.id}",
            headers=headers(admin),
            json={"roadmap_ids": [str(value) for value in ids]},
        )
        assert response.status_code == 409
    current = client.get(f"/api/v1/internships/{cohort.id}", headers=headers(admin)).json()
    assert set(current["roadmap_ids"]) == {str(value.id) for value in roadmaps.values()}
    assert {item["position"] for item in current["roadmaps"]} == {"BACKEND", "FULLSTACK"}


def test_in_use_mapping_cannot_be_removed_and_manual_assignment_cannot_mismatch(position_curricula):
    db, admin, interns, roadmaps, cohort, applications = position_curricula
    InternshipService.review_application(
        db, applications["BACKEND"].id, InternshipApplicationReview(status="APPROVED"), admin.id
    )
    member = db.scalar(
        select(InternshipMember).where(InternshipMember.intern_id == interns["BACKEND"].id)
    )
    with pytest.raises(HTTPException) as removed:
        InternshipService.update_internship(
            db, cohort.id, InternshipUpdate(roadmap_ids=[roadmaps["FULLSTACK"].id])
        )
    assert removed.value.status_code == 409
    with pytest.raises(HTTPException) as mismatched:
        InternshipService.update_member(
            db, member.id, InternshipMemberUpdate(roadmap_id=roadmaps["FULLSTACK"].id)
        )
    assert mismatched.value.status_code == 409
    db.refresh(member)
    assert member.roadmap_id == roadmaps["BACKEND"].id
    response = TestClient(app).patch(
        f"/api/v1/training/roadmaps/{roadmaps['BACKEND'].id}",
        headers=headers(admin),
        json={"position": "AI"},
    )
    assert response.status_code == 409
    assert (
        TestClient(app)
        .delete(f"/api/v1/training/roadmaps/{roadmaps['BACKEND'].id}", headers=headers(admin))
        .status_code
        == 409
    )


def test_safe_legacy_typing_requires_no_known_member_mismatch(position_curricula):
    db, admin, interns, _, cohort, _ = position_curricula
    legacy = Roadmap(name=f"Legacy {uuid.uuid4().hex}", status="ACTIVE")
    db.add(legacy)
    db.flush()
    member = InternshipMember(
        internship_id=cohort.id,
        intern_id=interns["AI"].id,
        position="AI",
        roadmap_id=legacy.id,
        status="ACTIVE",
    )
    db.add(member)
    db.commit()
    client = TestClient(app)
    url = f"/api/v1/training/roadmaps/{legacy.id}"
    assert (
        client.patch(url, headers=headers(admin), json={"position": "BACKEND"}).status_code == 409
    )
    assert client.patch(url, headers=headers(admin), json={"position": "AI"}).status_code == 200
    db.refresh(member)
    assert member.roadmap_id == legacy.id


def test_legacy_mismatch_can_be_repaired_without_configuration_deadlock(position_curricula):
    db, _, interns, roadmaps, cohort, _ = position_curricula
    legacy = Roadmap(name=f"Legacy mismatch {uuid.uuid4().hex}", status="ACTIVE")
    db.add(legacy)
    db.flush()
    member = InternshipMember(
        internship_id=cohort.id,
        intern_id=interns["BACKEND"].id,
        position="BACKEND",
        roadmap_id=legacy.id,
        status="ACTIVE",
    )
    db.add(member)
    db.commit()
    InternshipService.update_internship(
        db, cohort.id, InternshipUpdate(roadmap_ids=[value.id for value in roadmaps.values()])
    )
    db.refresh(member)
    assert member.roadmap_id == legacy.id
    updated = InternshipService.update_member(
        db, member.id, InternshipMemberUpdate(roadmap_id=roadmaps["BACKEND"].id)
    )
    assert updated.roadmap_id == roadmaps["BACKEND"].id


def test_retained_archived_mapping_does_not_autofill_unassigned_members(position_curricula):
    db, _, interns, roadmaps, cohort, _ = position_curricula
    member = InternshipMember(
        internship_id=cohort.id,
        intern_id=interns["BACKEND"].id,
        position="BACKEND",
        status="ACTIVE",
    )
    db.add(member)
    roadmaps["BACKEND"].status = "ARCHIVED"
    db.commit()
    InternshipService.update_internship(
        db, cohort.id, InternshipUpdate(roadmap_ids=[item.id for item in roadmaps.values()])
    )
    db.refresh(member)
    assert member.roadmap_id is None


def test_stale_cohort_identity_cannot_approve_after_cancellation(position_curricula):
    db, admin, _, _, cohort, applications = position_curricula
    cohort_id = cohort.id
    db.execute(
        update(Internship)
        .where(Internship.id == cohort_id)
        .values(status="CANCELLED")
        .execution_options(synchronize_session=False)
    )
    assert cohort.status == "OPEN"
    with pytest.raises(HTTPException) as error:
        InternshipService.review_application(
            db, applications["BACKEND"].id, InternshipApplicationReview(status="APPROVED"), admin.id
        )
    assert error.value.status_code == 400


def test_database_mapping_position_must_match_parent_roadmap(position_curricula):
    db, _, _, roadmaps, cohort, _ = position_curricula
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(
                InternshipRoadmap(
                    internship_id=cohort.id, position="AI", roadmap_id=roadmaps["BACKEND"].id
                )
            )
            db.flush()


def test_position_migration_does_not_guess_or_rewrite_history(position_curricula):
    db, _, interns, roadmaps, cohort, _ = position_curricula
    phase = Phase(roadmap_id=roadmaps["BACKEND"].id, name="Preserved phase", order_no=1)
    db.add(phase)
    db.flush()
    content = LearningContent(phase_id=phase.id, title="Preserved", type="LESSON", order_no=1)
    member = InternshipMember(
        internship_id=cohort.id,
        intern_id=interns["BACKEND"].id,
        position="BACKEND",
        roadmap_id=roadmaps["BACKEND"].id,
        status="ACTIVE",
    )
    db.add_all([content, member])
    db.flush()
    progress = LearningProgress(
        internship_member_id=member.id,
        content_id=content.id,
        status="COMPLETED",
        progress_percent=100,
    )
    db.add(progress)
    db.commit()
    ids = member.id, member.roadmap_id, progress.id
    migration = import_module("migrations.versions.0019_position_roadmaps")
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
        migration.upgrade()
    db.commit()
    db.expire_all()
    preserved = db.get(InternshipMember, ids[0])
    assert preserved.roadmap_id == ids[1]
    assert db.get(LearningProgress, ids[2]).progress_percent == 100
    assert db.get(Roadmap, ids[1]).position is None
    assert list(db.scalars(select(InternshipRoadmap))) == []
