import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
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
FINAL_OK = {
    "evaluation_type": "FINAL",
    "verdict": "PASS",
    "verdict_reason": "Hoàn thành tốt chương trình thực tập",
}

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
        json={"scores": _scores(ev, a=10, b=20), "evaluation_type": "PERIODIC", "comment": "Mới"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["total_score"] == 10.0
    assert updated.json()["evaluation_type"] == "PERIODIC"
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
    published_id = _create(client, ev, **FINAL_OK).json()["id"]
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
    final_id = _create(client, ev, **FINAL_OK).json()["id"]
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


# ── Nhận xét tuần (WEEKLY) ──────────────────────────────────────────────────


def _weekly(
    client,
    ev,
    *,
    start="2026-09-14",
    end="2026-09-20",
    mentor="mentor1",
    member="member_a",
    comment="Tuần này hoàn thành tốt",
    **extra,
):
    payload = {
        "internship_member_id": str(ev[member].id),
        "evaluation_type": "WEEKLY",
        "week_start": start,
        "week_end": end,
        "comment": comment,
        **extra,
    }
    return client.post(EVAL_URL, headers=_h(ev[mentor]), json=payload)


def test_weekly_create_has_range_and_no_scores(client, ev):
    resp = _weekly(client, ev)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["evaluation_type"] == "WEEKLY"
    assert body["week_start"] == "2026-09-14"
    assert body["week_end"] == "2026-09-20"
    assert body["comment"] == "Tuần này hoàn thành tốt"
    assert body["scores"] == []
    assert body["total_score"] is None
    assert body["verdict"] is None
    assert body["status"] == "DRAFT"
    assert body["intern_name"] == "Eval ia"


def test_weekly_requires_valid_week_range(client, ev):
    h = _h(ev["mentor1"])
    missing = client.post(
        EVAL_URL,
        headers=h,
        json={
            "internship_member_id": str(ev["member_a"].id),
            "evaluation_type": "WEEKLY",
            "comment": "x",
        },
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "WEEK_RANGE_REQUIRED"

    reversed_range = _weekly(client, ev, start="2026-09-20", end="2026-09-14")
    assert reversed_range.status_code == 422
    assert reversed_range.json()["error"]["code"] == "WEEK_RANGE_INVALID"

    too_long = _weekly(client, ev, start="2026-09-14", end="2026-10-05")
    assert too_long.status_code == 422
    assert too_long.json()["error"]["code"] == "WEEK_RANGE_TOO_LONG"

    # Đúng 14 ngày vẫn hợp lệ; một ngày đơn lẻ cũng hợp lệ.
    assert _weekly(client, ev, start="2026-10-01", end="2026-10-14").status_code == 201
    assert _weekly(client, ev, start="2026-11-01", end="2026-11-01").status_code == 201


def test_weekly_rejects_scores_and_verdict(client, ev):
    with_scores = _weekly(client, ev, scores=_scores(ev))
    assert with_scores.status_code == 422
    assert with_scores.json()["error"]["code"] == "WEEKLY_NO_SCORES"
    with_verdict = _weekly(client, ev, verdict="PASS")
    assert with_verdict.status_code == 422
    assert with_verdict.json()["error"]["code"] == "VERDICT_NOT_ALLOWED"


def test_week_range_and_verdict_only_for_their_types(client, ev):
    with_week = _create(client, ev, week_start="2026-09-14", week_end="2026-09-20")
    assert with_week.status_code == 422
    assert with_week.json()["error"]["code"] == "WEEK_NOT_ALLOWED"
    verdict_on_periodic = _create(client, ev, verdict="PASS")
    assert verdict_on_periodic.status_code == 422
    assert verdict_on_periodic.json()["error"]["code"] == "VERDICT_NOT_ALLOWED"
    reason_on_periodic = _create(client, ev, verdict_reason="Lý do")
    assert reason_on_periodic.status_code == 422


def test_weekly_overlap_is_rejected_per_intern(client, ev):
    assert _weekly(client, ev).status_code == 201
    overlap = _weekly(client, ev, start="2026-09-20", end="2026-09-26")
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "WEEK_OVERLAP"
    assert overlap.json()["error"]["details"]["week_start"] == "2026-09-14"

    # Tuần liền kề không trùng; Intern khác cùng tuần không bị ảnh hưởng.
    assert _weekly(client, ev, start="2026-09-21", end="2026-09-27").status_code == 201
    other = _weekly(client, ev, mentor="mentor2", member="member_b")
    assert other.status_code == 201


def test_weekly_update_draft_checks_overlap_and_type(client, ev):
    h = _h(ev["mentor1"])
    first = _weekly(client, ev).json()["id"]
    second = _weekly(client, ev, start="2026-09-21", end="2026-09-27").json()["id"]

    # Giữ nguyên khoảng của chính mình thì không tự xung đột.
    same = client.put(
        f"{EVAL_URL}/{first}",
        headers=h,
        json={"week_start": "2026-09-14", "week_end": "2026-09-20"},
    )
    assert same.status_code == 200, same.text
    clash = client.put(
        f"{EVAL_URL}/{second}",
        headers=h,
        json={"week_start": "2026-09-18", "week_end": "2026-09-24"},
    )
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "WEEK_OVERLAP"

    moved = client.put(
        f"{EVAL_URL}/{second}",
        headers=h,
        json={"week_start": "2026-09-28", "week_end": "2026-10-04", "comment": "Cập nhật"},
    )
    assert moved.status_code == 200
    assert moved.json()["week_start"] == "2026-09-28"
    assert moved.json()["comment"] == "Cập nhật"

    with_scores = client.put(f"{EVAL_URL}/{first}", headers=h, json={"scores": _scores(ev)})
    assert with_scores.status_code == 422
    assert with_scores.json()["error"]["code"] == "WEEKLY_NO_SCORES"
    change_type = client.put(f"{EVAL_URL}/{first}", headers=h, json={"evaluation_type": "PERIODIC"})
    assert change_type.status_code == 422
    assert change_type.json()["error"]["code"] == "TYPE_IMMUTABLE"


def test_weekly_publish_requires_content_and_locks(client, ev):
    h = _h(ev["mentor1"])
    weekly_id = _weekly(client, ev, comment=None).json()["id"]
    blocked = client.post(f"{EVAL_URL}/{weekly_id}/publish", headers=h)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "WEEKLY_CONTENT_REQUIRED"

    client.put(f"{EVAL_URL}/{weekly_id}", headers=h, json={"comment": "   "})
    assert client.post(f"{EVAL_URL}/{weekly_id}/publish", headers=h).status_code == 409

    client.put(f"{EVAL_URL}/{weekly_id}", headers=h, json={"comment": "Làm tốt tuần này"})
    published = client.post(f"{EVAL_URL}/{weekly_id}/publish", headers=h)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "PUBLISHED"
    assert published.json()["total_score"] is None
    assert published.json()["published_at"]

    edit = client.put(f"{EVAL_URL}/{weekly_id}", headers=h, json={"comment": "sửa"})
    assert edit.status_code == 409
    assert edit.json()["error"]["code"] == "EVALUATION_ALREADY_PUBLISHED"


def test_weekly_does_not_need_any_criteria(client, ev):
    for key in ("crit_a", "crit_b"):
        client.put(
            f"{CRITERIA_URL}/{ev[key].id}", headers=_h(ev["admin"]), json={"status": "INACTIVE"}
        )
    weekly_id = _weekly(client, ev).json()["id"]
    published = client.post(f"{EVAL_URL}/{weekly_id}/publish", headers=_h(ev["mentor1"]))
    assert published.status_code == 200, published.text


def test_intern_sees_only_published_weekly_of_self(client, ev):
    mentor = _h(ev["mentor1"])
    intern = _h(ev["intern_a"])
    draft_id = _weekly(client, ev, start="2026-09-21", end="2026-09-27").json()["id"]
    published_id = _weekly(client, ev).json()["id"]
    client.post(f"{EVAL_URL}/{published_id}/publish", headers=mentor)
    other_id = _weekly(client, ev, mentor="mentor2", member="member_b").json()["id"]
    client.post(f"{EVAL_URL}/{other_id}/publish", headers=_h(ev["mentor2"]))

    listing = client.get(EVAL_URL, params={"evaluation_type": "WEEKLY"}, headers=intern).json()
    assert [e["id"] for e in listing] == [published_id]
    assert listing[0]["week_start"] == "2026-09-14"
    assert listing[0]["comment"] == "Tuần này hoàn thành tốt"
    assert client.get(f"{EVAL_URL}/{draft_id}", headers=intern).status_code == 404
    assert client.get(f"{EVAL_URL}/{other_id}", headers=intern).status_code == 404


def test_other_mentor_cannot_touch_weekly(client, ev):
    weekly_id = _weekly(client, ev).json()["id"]
    h2 = _h(ev["mentor2"])
    assert client.get(f"{EVAL_URL}/{weekly_id}", headers=h2).status_code == 404
    assert (
        client.put(f"{EVAL_URL}/{weekly_id}", headers=h2, json={"comment": "x"}).status_code == 404
    )
    assert client.post(f"{EVAL_URL}/{weekly_id}/publish", headers=h2).status_code == 404
    assert _weekly(client, ev, mentor="mentor2", member="member_a").status_code == 404


# ── Đánh giá cuối cùng (FINAL): Đạt / Chưa đạt kèm lý do ───────────────────


def test_final_publish_requires_verdict_and_reason(client, ev):
    h = _h(ev["mentor1"])
    final_id = _create(client, ev, evaluation_type="FINAL").json()["id"]
    no_verdict = client.post(f"{EVAL_URL}/{final_id}/publish", headers=h)
    assert no_verdict.status_code == 409
    assert no_verdict.json()["error"]["code"] == "FINAL_VERDICT_REQUIRED"

    client.put(f"{EVAL_URL}/{final_id}", headers=h, json={"verdict": "PASS"})
    assert client.post(f"{EVAL_URL}/{final_id}/publish", headers=h).status_code == 409

    client.put(f"{EVAL_URL}/{final_id}", headers=h, json={"verdict_reason": "  Hoàn thành tốt  "})
    published = client.post(f"{EVAL_URL}/{final_id}/publish", headers=h)
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "PUBLISHED"
    assert body["verdict"] == "PASS"
    assert body["verdict_reason"] == "Hoàn thành tốt"
    assert body["total_score"] == 7.8


def test_final_still_needs_complete_scores(client, ev):
    final_id = _create(client, ev, scores=_scores(ev, b=None), **FINAL_OK).json()["id"]
    resp = client.post(f"{EVAL_URL}/{final_id}/publish", headers=_h(ev["mentor1"]))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INCOMPLETE_EVALUATION"


def test_final_discards_comments_on_create_and_update(client, ev):
    created = _create(client, ev, comment="Unwanted comment", **FINAL_OK)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["comment"] is None
    evaluation_id = uuid.UUID(body["id"])
    session = ev["session"]
    assert session.get(Evaluation, evaluation_id).comment is None

    updated = client.put(
        f"{EVAL_URL}/{evaluation_id}",
        headers=_h(ev["mentor1"]),
        json={"comment": "Another unwanted comment"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["comment"] is None
    session.expire_all()
    assert session.get(Evaluation, evaluation_id).comment is None


@pytest.mark.parametrize("action", ["update", "publish"])
def test_final_clears_legacy_comment_when_saved(client, ev, action):
    body = _create(client, ev, **FINAL_OK).json()
    session = ev["session"]
    evaluation = session.get(Evaluation, uuid.UUID(body["id"]))
    evaluation.comment = "Legacy final comment"
    session.commit()

    read = client.get(f"{EVAL_URL}/{body['id']}", headers=_h(ev["mentor1"]))
    assert read.json()["comment"] is None
    if action == "update":
        saved = client.put(f"{EVAL_URL}/{body['id']}", headers=_h(ev["mentor1"]), json={})
    else:
        saved = client.post(f"{EVAL_URL}/{body['id']}/publish", headers=_h(ev["mentor1"]))
    assert saved.status_code == 200, saved.text
    assert saved.json()["comment"] is None
    assert saved.json()["verdict_reason"] == FINAL_OK["verdict_reason"]
    session.refresh(evaluation)
    assert evaluation.comment is None


def test_final_comment_migration_preserves_other_types_and_verdict(client, ev, monkeypatch):
    final = _create(client, ev, **FINAL_OK).json()
    periodic = _create(client, ev, comment="Periodic comment").json()
    weekly = _weekly(client, ev, comment="Weekly comment").json()
    session = ev["session"]
    stored_final = session.get(Evaluation, uuid.UUID(final["id"]))
    stored_final.comment = "Obsolete final comment"
    session.commit()
    migration = import_module("migrations.versions.0013_final_no_comment")
    monkeypatch.setattr(
        migration, "op", Operations(MigrationContext.configure(session.connection()))
    )
    migration.upgrade()
    session.expire_all()
    assert session.get(Evaluation, uuid.UUID(final["id"])).comment is None
    assert (
        session.get(Evaluation, uuid.UUID(final["id"])).verdict_reason == FINAL_OK["verdict_reason"]
    )
    assert session.get(Evaluation, uuid.UUID(periodic["id"])).comment == "Periodic comment"
    assert session.get(Evaluation, uuid.UUID(weekly["id"])).comment == "Weekly comment"


def test_intern_sees_fail_verdict_with_reason(client, ev):
    final = _create(
        client,
        ev,
        evaluation_type="FINAL",
        verdict="FAIL",
        verdict_reason="Chưa đạt yêu cầu về tiến độ",
    ).json()
    client.post(f"{EVAL_URL}/{final['id']}/publish", headers=_h(ev["mentor1"]))
    seen = client.get(f"{EVAL_URL}/{final['id']}", headers=_h(ev["intern_a"])).json()
    assert seen["verdict"] == "FAIL"
    assert seen["verdict_reason"] == "Chưa đạt yêu cầu về tiến độ"
    assert seen["evaluation_type"] == "FINAL"


def test_only_one_final_per_intern(client, ev):
    assert _create(client, ev, **FINAL_OK).status_code == 201
    duplicate = _create(client, ev, **FINAL_OK)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "FINAL_EXISTS"
    other = _create(client, ev, mentor="mentor2", member="member_b", **FINAL_OK)
    assert other.status_code == 201
    # Vẫn tạo được các loại đánh giá khác cho cùng Intern.
    assert _create(client, ev).status_code == 201
    assert _weekly(client, ev).status_code == 201


def test_evaluation_type_cannot_change_after_creation(client, ev):
    evaluation_id = _create(client, ev).json()["id"]
    resp = client.put(
        f"{EVAL_URL}/{evaluation_id}", headers=_h(ev["mentor1"]), json={"evaluation_type": "FINAL"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "TYPE_IMMUTABLE"


def test_list_filters_include_weekly_type(client, ev):
    mentor = _h(ev["mentor1"])
    periodic_id = _create(client, ev).json()["id"]
    weekly_id = _weekly(client, ev).json()["id"]
    weekly = client.get(EVAL_URL, params={"evaluation_type": "WEEKLY"}, headers=mentor).json()
    assert [e["id"] for e in weekly] == [weekly_id]
    periodic = client.get(EVAL_URL, params={"evaluation_type": "PERIODIC"}, headers=mentor).json()
    assert [e["id"] for e in periodic] == [periodic_id]
    admin = client.get(EVAL_URL, params={"evaluation_type": "WEEKLY"}, headers=_h(ev["admin"]))
    assert weekly_id in {e["id"] for e in admin.json()}


def test_latest_dashboard_score_ignores_weekly_comments(client, ev):
    mentor = _h(ev["mentor1"])
    scored = _create(client, ev).json()["id"]
    client.post(f"{EVAL_URL}/{scored}/publish", headers=mentor)
    weekly = _weekly(client, ev).json()["id"]
    client.post(f"{EVAL_URL}/{weekly}/publish", headers=mentor)

    board = client.get("/api/v1/dashboard", headers=_h(ev["intern_a"])).json()
    metric = next(m for m in board["metrics"] if m["key"] == "latest_evaluation_score")
    assert metric["value"] == 7.8


def test_database_constraints_guard_the_new_rules(ev):
    from sqlalchemy.exc import IntegrityError

    session = ev["session"]
    now = datetime.now(UTC)

    def add(**kwargs):
        base = {
            "internship_member_id": ev["member_a"].id,
            "mentor_id": ev["mentor1"].id,
            "criteria_scores": [],
            "status": "DRAFT",
            "created_at": now,
            "updated_at": now,
        }
        session.add(Evaluation(**{**base, **kwargs}))

    invalid_rows = [
        {"evaluation_type": "WEEKLY"},
        {
            "evaluation_type": "WEEKLY",
            "week_start": date(2026, 9, 20),
            "week_end": date(2026, 9, 14),
        },
        {
            "evaluation_type": "PERIODIC",
            "week_start": date(2026, 9, 14),
            "week_end": date(2026, 9, 20),
        },
        {"evaluation_type": "PERIODIC", "verdict": "PASS"},
        {"evaluation_type": "FINAL", "verdict": "MAYBE"},
    ]
    for row in invalid_rows:
        add(**row)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    add(evaluation_type="FINAL")
    session.commit()
    add(evaluation_type="FINAL")  # đánh giá cuối cùng thứ hai của cùng một Intern
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
