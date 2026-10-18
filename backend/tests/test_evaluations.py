import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.db.session import get_session_factory
from app.main import app
from app.models import (
    Evaluation,
    EvaluationCriterion,
    Internship,
    InternshipMember,
    User,
)
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.services.evaluation import compute_total

CRITERIA_URL = "/api/v1/evaluation-criteria"
EVAL_URL = "/api/v1/evaluations"

# ---------------------------------------------------------------------------
# Tính tổng điểm (không cần database)
# ---------------------------------------------------------------------------


def test_compute_total_matches_seed_example():
    items = [
        {"score": 8.5, "max_score": 10, "weight": 40},
        {"score": 9, "max_score": 10, "weight": 30},
        {"score": 9, "max_score": 10, "weight": 30},
    ]
    assert compute_total(items) == 8.8


def test_compute_total_normalizes_scale_and_weights():
    # Thang điểm khác nhau và tổng trọng số khác 100 vẫn quy về thang 10.
    items = [
        {"score": 8, "max_score": 10, "weight": 3},
        {"score": 15, "max_score": 20, "weight": 2},
    ]
    assert compute_total(items) == 7.8
    assert compute_total([{"score": 5, "max_score": 10, "weight": 0}]) == 5.0
    assert compute_total([]) == 0.0


# ---------------------------------------------------------------------------
# API với database thật
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _user(suffix: str, tag: str, role: UserRole) -> User:
    return User(
        email=f"evl_{tag}_{suffix}@ex.com",
        password_hash="h",
        full_name=f"Eval {tag}",
        role=role,
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def ev() -> Generator[dict]:
    session = get_session_factory()()
    suffix = uuid.uuid4().hex[:8]

    admin = _user(suffix, "admin", UserRole.ADMIN)
    mentor1 = _user(suffix, "m1", UserRole.MENTOR)
    mentor2 = _user(suffix, "m2", UserRole.MENTOR)
    intern_a = _user(suffix, "ia", UserRole.INTERN)
    intern_b = _user(suffix, "ib", UserRole.INTERN)
    session.add_all([admin, mentor1, mentor2, intern_a, intern_b])
    session.commit()

    # Tạm ngừng các tiêu chí có sẵn (dữ liệu seed) để kết quả test xác định.
    seeded_active = [
        row.id
        for row in session.scalars(
            select(EvaluationCriterion).where(EvaluationCriterion.status == "ACTIVE")
        )
    ]
    if seeded_active:
        session.execute(
            update(EvaluationCriterion)
            .where(EvaluationCriterion.id.in_(seeded_active))
            .values(status="INACTIVE")
        )
    crit_a = EvaluationCriterion(
        name=f"EV Chuyên môn {suffix}", max_score=10, weight=60, status="ACTIVE"
    )
    crit_b = EvaluationCriterion(
        name=f"EV Thái độ {suffix}", max_score=20, weight=40, status="ACTIVE"
    )
    session.add_all([crit_a, crit_b])
    session.commit()

    internship = Internship(
        name=f"EV {suffix}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 12, 31),
        status=InternshipStatus.ONGOING,
        created_by=admin.id,
    )
    session.add(internship)
    session.commit()
    member_a = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_a.id,
        mentor_id=mentor1.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor2.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add_all([member_a, member_b])
    session.commit()

    data = {
        "session": session,
        "suffix": suffix,
        "admin": admin,
        "mentor1": mentor1,
        "mentor2": mentor2,
        "intern_a": intern_a,
        "intern_b": intern_b,
        "member_a": member_a,
        "member_b": member_b,
        "crit_a": crit_a,
        "crit_b": crit_b,
    }
    yield data

    session.rollback()
    session.execute(delete(Internship).where(Internship.id == internship.id))
    session.execute(delete(EvaluationCriterion).where(EvaluationCriterion.name.like(f"%{suffix}%")))
    if seeded_active:
        session.execute(
            update(EvaluationCriterion)
            .where(EvaluationCriterion.id.in_(seeded_active))
            .values(status="ACTIVE")
        )
    session.execute(
        delete(User).where(
            User.id.in_([admin.id, mentor1.id, mentor2.id, intern_a.id, intern_b.id])
        )
    )
    session.commit()
    session.close()


def _h(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def _scores(ev: dict, a: float | None = 8, b: float | None = 15) -> list[dict]:
    items = []
    if a is not None:
        items.append({"criterion_id": str(ev["crit_a"].id), "score": a})
    if b is not None:
        items.append({"criterion_id": str(ev["crit_b"].id), "score": b})
    return items


def _create(client, ev, *, mentor="mentor1", member="member_a", scores=None, **extra):
    payload = {
        "internship_member_id": str(ev[member].id),
        "evaluation_type": "PERIODIC",
        "scores": _scores(ev) if scores is None else scores,
        "comment": "Nhận xét",
        **extra,
    }
    return client.post(EVAL_URL, headers=_h(ev[mentor]), json=payload)


# ── Tiêu chí: phân quyền và dữ liệu hợp lệ ─────────────────────────────────


def test_criteria_permissions(client, ev):
    assert client.get(CRITERIA_URL).status_code == 401
    assert client.get(CRITERIA_URL, headers=_h(ev["intern_a"])).status_code == 403

    body = {"name": f"EV mới {ev['suffix']}", "max_score": 10, "weight": 10}
    assert client.post(CRITERIA_URL, headers=_h(ev["mentor1"]), json=body).status_code == 403
    assert client.post(CRITERIA_URL, headers=_h(ev["intern_a"]), json=body).status_code == 403
    created = client.post(CRITERIA_URL, headers=_h(ev["admin"]), json=body)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "ACTIVE"

    crit = str(ev["crit_a"].id)
    assert (
        client.put(f"{CRITERIA_URL}/{crit}", headers=_h(ev["mentor1"]), json={"weight": 5})
    ).status_code == 403
    assert client.delete(f"{CRITERIA_URL}/{crit}", headers=_h(ev["mentor1"])).status_code == 403


def test_mentor_lists_only_active_criteria_admin_sees_all(client, ev):
    client.put(
        f"{CRITERIA_URL}/{ev['crit_b'].id}", headers=_h(ev["admin"]), json={"status": "INACTIVE"}
    )
    mentor_view = client.get(CRITERIA_URL, headers=_h(ev["mentor1"])).json()
    mentor_names = {c["name"] for c in mentor_view["items"]}
    assert ev["crit_a"].name in mentor_names
    assert ev["crit_b"].name not in mentor_names

    admin_view = client.get(CRITERIA_URL, headers=_h(ev["admin"])).json()
    assert ev["crit_b"].name in {c["name"] for c in admin_view["items"]}
    inactive_only = client.get(
        CRITERIA_URL, params={"status": "INACTIVE"}, headers=_h(ev["admin"])
    ).json()
    assert {c["status"] for c in inactive_only["items"]} == {"INACTIVE"}


def test_criteria_total_active_weight(client, ev):
    body = client.get(CRITERIA_URL, headers=_h(ev["admin"])).json()
    assert body["total_active_weight"] == 100


def test_criteria_validation_and_duplicate_name(client, ev):
    h = _h(ev["admin"])
    bad_max = client.post(CRITERIA_URL, headers=h, json={"name": "x", "max_score": 0, "weight": 5})
    assert bad_max.status_code == 422
    bad_weight = client.post(
        CRITERIA_URL, headers=h, json={"name": "x", "max_score": 10, "weight": 101}
    )
    assert bad_weight.status_code == 422
    blank = client.post(CRITERIA_URL, headers=h, json={"name": "   ", "max_score": 10, "weight": 5})
    assert blank.status_code == 422

    duplicate = client.post(
        CRITERIA_URL,
        headers=h,
        json={"name": ev["crit_a"].name.upper(), "max_score": 10, "weight": 5},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CRITERION_NAME_EXISTS"

    rename_clash = client.put(
        f"{CRITERIA_URL}/{ev['crit_b'].id}", headers=h, json={"name": ev["crit_a"].name}
    )
    assert rename_clash.status_code == 409


def test_update_and_delete_criterion(client, ev):
    h = _h(ev["admin"])
    updated = client.put(
        f"{CRITERIA_URL}/{ev['crit_a'].id}",
        headers=h,
        json={"weight": 70, "max_score": 5, "description": "Mô tả mới"},
    )
    assert updated.status_code == 200
    assert updated.json()["weight"] == 70
    assert updated.json()["max_score"] == 5
    assert updated.json()["name"] == ev["crit_a"].name

    assert client.put(f"{CRITERIA_URL}/{uuid.uuid4()}", headers=h, json={}).status_code == 404

    spare = client.post(
        CRITERIA_URL,
        headers=h,
        json={"name": f"EV tạm {ev['suffix']}", "max_score": 10, "weight": 0},
    ).json()
    assert client.delete(f"{CRITERIA_URL}/{spare['id']}", headers=h).status_code == 204
    assert client.delete(f"{CRITERIA_URL}/{spare['id']}", headers=h).status_code == 404


def test_cannot_delete_criterion_used_by_evaluation(client, ev):
    assert _create(client, ev).status_code == 201
    resp = client.delete(f"{CRITERIA_URL}/{ev['crit_a'].id}", headers=_h(ev["admin"]))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CRITERION_IN_USE"


# ── Mentor lập và sửa nháp ──────────────────────────────────────────────────


def test_mentor_creates_complete_draft_with_total(client, ev):
    resp = _create(client, ev)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "DRAFT"
    assert body["published_at"] is None
    assert body["total_score"] == 7.8
    assert body["intern_name"] == "Eval ia"
    assert body["mentor_name"] == "Eval m1"
    assert [s["name"] for s in body["scores"]] == [ev["crit_a"].name, ev["crit_b"].name]
    assert body["scores"][0]["max_score"] == 10
    assert body["scores"][0]["weight"] == 60


def test_partial_draft_has_no_total(client, ev):
    resp = _create(client, ev, scores=_scores(ev, b=None))
    assert resp.status_code == 201
    assert resp.json()["total_score"] is None
    empty = _create(client, ev, scores=[])
    assert empty.status_code == 201
    assert empty.json()["scores"] == []


def test_score_validation(client, ev):
    too_high = _create(client, ev, scores=_scores(ev, a=11))
    assert too_high.status_code == 422
    assert too_high.json()["error"]["code"] == "SCORE_OUT_OF_RANGE"
    assert _create(client, ev, scores=_scores(ev, a=-1)).status_code == 422
    unknown = _create(client, ev, scores=[{"criterion_id": str(uuid.uuid4()), "score": 5}])
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "INVALID_CRITERION"
    duplicate = _create(client, ev, scores=_scores(ev) + _scores(ev, b=None))
    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["code"] == "DUPLICATE_CRITERION"

    client.put(
        f"{CRITERIA_URL}/{ev['crit_b'].id}", headers=_h(ev["admin"]), json={"status": "INACTIVE"}
    )
    inactive = _create(client, ev, scores=_scores(ev))
    assert inactive.status_code == 422


def test_mentor_can_only_evaluate_own_interns(client, ev):
    other = _create(client, ev, mentor="mentor2", member="member_a")
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "MEMBER_NOT_FOUND"
    assert _create(client, ev, mentor="mentor2", member="member_b").status_code == 201

    ghost = client.post(
        EVAL_URL,
        headers=_h(ev["mentor1"]),
        json={"internship_member_id": str(uuid.uuid4()), "scores": []},
    )
    assert ghost.status_code == 404


def test_other_mentor_cannot_read_update_or_publish(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    h2 = _h(ev["mentor2"])
    assert client.get(f"{EVAL_URL}/{evaluation_id}", headers=h2).status_code == 404
    assert (
        client.put(f"{EVAL_URL}/{evaluation_id}", headers=h2, json={"comment": "x"})
    ).status_code == 404
    assert client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h2).status_code == 404
    assert client.get(EVAL_URL, headers=h2).json() == []


def test_update_draft(client, ev):
    h = _h(ev["mentor1"])
    evaluation_id = _create(client, ev, scores=_scores(ev, b=None)).json()["id"]

    updated = client.put(
        f"{EVAL_URL}/{evaluation_id}",
        headers=h,
        json={"scores": _scores(ev, a=10, b=20), "evaluation_type": "FINAL", "comment": "Mới"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["total_score"] == 10.0
    assert updated.json()["evaluation_type"] == "FINAL"
    assert updated.json()["comment"] == "Mới"

    # Không gửi scores thì giữ nguyên điểm; comment = null thì xóa nhận xét.
    cleared = client.put(f"{EVAL_URL}/{evaluation_id}", headers=h, json={"comment": None})
    assert cleared.json()["comment"] is None
    assert cleared.json()["total_score"] == 10.0
    assert len(cleared.json()["scores"]) == 2


# ── Công bố ─────────────────────────────────────────────────────────────────


def test_publish_requires_complete_scores(client, ev):
    h = _h(ev["mentor1"])
    evaluation_id = _create(client, ev, scores=_scores(ev, b=None)).json()["id"]
    resp = client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INCOMPLETE_EVALUATION"
    assert resp.json()["error"]["details"]["missing_criteria"] == [ev["crit_b"].name]
    still = client.get(f"{EVAL_URL}/{evaluation_id}", headers=h).json()
    assert still["status"] == "DRAFT"


def test_publish_locks_evaluation(client, ev):
    h = _h(ev["mentor1"])
    evaluation_id = _create(client, ev).json()["id"]
    published = client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h)
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "PUBLISHED"
    assert body["published_at"]
    assert body["total_score"] == 7.8

    edit = client.put(f"{EVAL_URL}/{evaluation_id}", headers=h, json={"comment": "sửa"})
    assert edit.status_code == 409
    assert edit.json()["error"]["code"] == "EVALUATION_ALREADY_PUBLISHED"
    again = client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h)
    assert again.status_code == 409


def test_publish_without_active_criteria(client, ev):
    evaluation_id = _create(client, ev, scores=[]).json()["id"]
    for key in ("crit_a", "crit_b"):
        client.put(
            f"{CRITERIA_URL}/{ev[key].id}", headers=_h(ev["admin"]), json={"status": "INACTIVE"}
        )
    resp = client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=_h(ev["mentor1"]))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "NO_ACTIVE_CRITERIA"


def test_publish_drops_deactivated_criteria(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    client.put(
        f"{CRITERIA_URL}/{ev['crit_b'].id}", headers=_h(ev["admin"]), json={"status": "INACTIVE"}
    )
    resp = client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=_h(ev["mentor1"]))
    assert resp.status_code == 200, resp.text
    assert [s["name"] for s in resp.json()["scores"]] == [ev["crit_a"].name]
    assert resp.json()["total_score"] == 8.0


def test_published_evaluation_keeps_criteria_snapshot(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=_h(ev["mentor1"]))

    client.put(
        f"{CRITERIA_URL}/{ev['crit_a'].id}",
        headers=_h(ev["admin"]),
        json={"name": f"EV đổi tên {ev['suffix']}", "weight": 5, "max_score": 100},
    )
    seen = client.get(f"{EVAL_URL}/{evaluation_id}", headers=_h(ev["intern_a"])).json()
    first = seen["scores"][0]
    assert first["name"] == ev["crit_a"].name
    assert first["weight"] == 60
    assert first["max_score"] == 10
    assert seen["total_score"] == 7.8


# ── Intern và Admin ─────────────────────────────────────────────────────────


def test_intern_sees_only_own_published_evaluations(client, ev):
    mentor = _h(ev["mentor1"])
    intern = _h(ev["intern_a"])
    draft_id = _create(client, ev).json()["id"]
    published_id = _create(client, ev, evaluation_type="FINAL").json()["id"]
    client.post(f"{EVAL_URL}/{published_id}/publish", headers=mentor)
    other_intern_id = _create(client, ev, mentor="mentor2", member="member_b").json()["id"]
    client.post(f"{EVAL_URL}/{other_intern_id}/publish", headers=_h(ev["mentor2"]))

    listing = client.get(EVAL_URL, headers=intern).json()
    assert [e["id"] for e in listing] == [published_id]
    assert {e["status"] for e in listing} == {"PUBLISHED"}

    draft = client.get(f"{EVAL_URL}/{draft_id}", headers=intern)
    assert draft.status_code == 404
    assert client.get(f"{EVAL_URL}/{published_id}", headers=intern).status_code == 200
    assert client.get(f"{EVAL_URL}/{other_intern_id}", headers=intern).status_code == 404
    # Lọc DRAFT cũng không làm lộ bản nháp.
    assert client.get(EVAL_URL, params={"status": "DRAFT"}, headers=intern).json() == []


def test_intern_cannot_write_evaluations(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    h = _h(ev["intern_a"])
    body = {"internship_member_id": str(ev["member_a"].id), "scores": []}
    assert client.post(EVAL_URL, headers=h, json=body).status_code == 403
    assert client.put(f"{EVAL_URL}/{evaluation_id}", headers=h, json={}).status_code == 403
    assert client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h).status_code == 403


def test_admin_reads_drafts_but_cannot_write(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    h = _h(ev["admin"])

    listing = client.get(EVAL_URL, headers=h).json()
    assert evaluation_id in {e["id"] for e in listing}
    assert client.get(f"{EVAL_URL}/{evaluation_id}", headers=h).status_code == 200

    body = {"internship_member_id": str(ev["member_a"].id), "scores": []}
    assert client.post(EVAL_URL, headers=h, json=body).status_code == 403
    assert client.put(f"{EVAL_URL}/{evaluation_id}", headers=h, json={}).status_code == 403
    assert client.post(f"{EVAL_URL}/{evaluation_id}/publish", headers=h).status_code == 403


def test_list_filters(client, ev):
    mentor = _h(ev["mentor1"])
    draft_id = _create(client, ev).json()["id"]
    final_id = _create(client, ev, evaluation_type="FINAL").json()["id"]
    client.post(f"{EVAL_URL}/{final_id}/publish", headers=mentor)

    published = client.get(EVAL_URL, params={"status": "PUBLISHED"}, headers=mentor).json()
    assert [e["id"] for e in published] == [final_id]
    drafts = client.get(EVAL_URL, params={"status": "DRAFT"}, headers=mentor).json()
    assert [e["id"] for e in drafts] == [draft_id]
    finals = client.get(EVAL_URL, params={"evaluation_type": "FINAL"}, headers=mentor).json()
    assert [e["id"] for e in finals] == [final_id]
    by_member = client.get(
        EVAL_URL, params={"member_id": str(ev["member_a"].id)}, headers=mentor
    ).json()
    assert len(by_member) == 2
    none = client.get(EVAL_URL, params={"member_id": str(ev["member_b"].id)}, headers=mentor)
    assert none.json() == []


def test_legacy_seed_format_is_readable(client, ev):
    """Đánh giá do seed tạo chỉ có {criterion_id, score}, không có bản chụp tiêu chí."""
    session = ev["session"]
    now = datetime.now(UTC)
    legacy = Evaluation(
        internship_member_id=ev["member_a"].id,
        mentor_id=ev["mentor1"].id,
        evaluation_type="PERIODIC",
        criteria_scores=[{"criterion_id": str(ev["crit_a"].id), "score": 8.5}],
        total_score=8.5,
        comment="Dữ liệu cũ",
        status="PUBLISHED",
        published_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(legacy)
    session.commit()

    resp = client.get(f"{EVAL_URL}/{legacy.id}", headers=_h(ev["intern_a"]))
    assert resp.status_code == 200
    score = resp.json()["scores"][0]
    assert score["name"] == ev["crit_a"].name
    assert score["max_score"] == 10
    assert score["score"] == 8.5
