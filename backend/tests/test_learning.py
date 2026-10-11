import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import get_session_factory
from app.main import app
from app.models import (
    Internship,
    InternshipMember,
    LearningContent,
    LearningProgress,
    Phase,
    Question,
    Quiz,
    QuizAttempt,
    Roadmap,
    User,
)
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.services.learning import (
    correct_keys,
    grade_question,
    normalize_options,
)

# ---------------------------------------------------------------------------
# Chấm điểm (không cần database)
# ---------------------------------------------------------------------------

ADMIN_STYLE_OPTIONS = [{"key": "A", "text": "git branch"}, {"key": "B", "text": "git commit"}]


def test_normalize_options_supports_admin_and_seed_formats():
    assert normalize_options(ADMIN_STYLE_OPTIONS, "SINGLE_CHOICE") == ADMIN_STYLE_OPTIONS
    assert normalize_options(["x", "y"], "SINGLE_CHOICE") == [
        {"key": "A", "text": "x"},
        {"key": "B", "text": "y"},
    ]
    assert normalize_options([True, False], "TRUE_FALSE") == [
        {"key": "A", "text": "Đúng"},
        {"key": "B", "text": "Sai"},
    ]
    assert normalize_options(None, "TRUE_FALSE")[0]["text"] == "Đúng"
    assert normalize_options(["ignored"], "TEXT") == []


def test_correct_keys_supports_admin_and_seed_formats():
    options = normalize_options(ADMIN_STYLE_OPTIONS, "SINGLE_CHOICE")
    assert correct_keys(["A"], options, "SINGLE_CHOICE") == {"A"}
    assert correct_keys("git commit", options, "SINGLE_CHOICE") == {"B"}
    assert correct_keys("unknown", options, "SINGLE_CHOICE") == set()

    tf = normalize_options([True, False], "TRUE_FALSE")
    assert correct_keys(True, tf, "TRUE_FALSE") == {"A"}
    assert correct_keys(False, tf, "TRUE_FALSE") == {"B"}
    assert correct_keys(["B"], tf, "TRUE_FALSE") == {"B"}


def test_grade_question_single_multiple_text():
    options = normalize_options(ADMIN_STYLE_OPTIONS, "SINGLE_CHOICE")
    assert grade_question("SINGLE_CHOICE", options, ["A"], ["A"], None) is True
    assert grade_question("SINGLE_CHOICE", options, ["A"], ["B"], None) is False
    assert grade_question("SINGLE_CHOICE", options, ["A"], [], None) is False

    multi = [{"key": "A", "text": "1"}, {"key": "B", "text": "2"}, {"key": "C", "text": "3"}]
    assert grade_question("MULTIPLE_CHOICE", multi, ["A", "C"], ["C", "A"], None) is True
    assert grade_question("MULTIPLE_CHOICE", multi, ["A", "C"], ["A"], None) is False
    assert grade_question("MULTIPLE_CHOICE", multi, ["A", "C"], ["A", "B", "C"], None) is False

    assert grade_question("TEXT", [], ["Hà  Nội"], [], " hà nội ") is True
    assert grade_question("TEXT", [], ["Hà Nội"], [], "Huế") is False
    # Chưa có đáp án mẫu thì không chấm tự động.
    assert grade_question("TEXT", [], [""], [], "bất kỳ") is None
    assert grade_question("SINGLE_CHOICE", options, None, ["A"], None) is None


# ---------------------------------------------------------------------------
# API với database thật
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _user(suffix: str, tag: str, role: UserRole) -> User:
    return User(
        email=f"lrn_{tag}_{suffix}@ex.com",
        password_hash="h",
        full_name=f"Learning {tag}",
        role=role,
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def learning_data() -> Generator[dict]:
    session = get_session_factory()()
    suffix = uuid.uuid4().hex[:8]

    admin = _user(suffix, "admin", UserRole.ADMIN)
    mentor = _user(suffix, "mentor", UserRole.MENTOR)
    intern_a = _user(suffix, "ia", UserRole.INTERN)
    intern_b = _user(suffix, "ib", UserRole.INTERN)
    intern_c = _user(suffix, "ic", UserRole.INTERN)  # chưa được giao lộ trình
    session.add_all([admin, mentor, intern_a, intern_b, intern_c])
    session.commit()

    roadmap = Roadmap(name=f"RM active {suffix}", status="ACTIVE", created_by=admin.id)
    other_roadmap = Roadmap(name=f"RM other {suffix}", status="ACTIVE", created_by=admin.id)
    draft_roadmap = Roadmap(name=f"RM draft {suffix}", status="DRAFT", created_by=admin.id)
    session.add_all([roadmap, other_roadmap, draft_roadmap])
    session.commit()

    phase1 = Phase(roadmap_id=roadmap.id, name="Phase 1", order_no=1)
    phase2 = Phase(roadmap_id=roadmap.id, name="Phase 2", order_no=2)
    other_phase = Phase(roadmap_id=other_roadmap.id, name="Other phase", order_no=1)
    session.add_all([phase1, phase2, other_phase])
    session.commit()

    contents = [
        LearningContent(
            phase_id=phase1.id, title="C1", type="LESSON", content="Body 1", order_no=1
        ),
        LearningContent(phase_id=phase1.id, title="C2", type="VIDEO", order_no=2),
        LearningContent(phase_id=phase2.id, title="C3", type="DOCUMENT", order_no=1),
        LearningContent(phase_id=phase2.id, title="C4", type="LINK", order_no=2),
    ]
    other_content = LearningContent(
        phase_id=other_phase.id, title="Other", type="LESSON", order_no=1
    )
    session.add_all([*contents, other_content])

    quiz = Quiz(
        phase_id=phase1.id,
        title="Quiz 1",
        duration_minutes=30,
        pass_score=60,
        max_attempts=2,
        status="PUBLISHED",
    )
    draft_quiz = Quiz(
        phase_id=phase1.id,
        title="Quiz draft",
        duration_minutes=10,
        pass_score=50,
        max_attempts=1,
        status="DRAFT",
    )
    closed_quiz = Quiz(
        phase_id=phase1.id,
        title="Quiz closed",
        duration_minutes=10,
        pass_score=50,
        max_attempts=1,
        status="CLOSED",
    )
    other_quiz = Quiz(
        phase_id=other_phase.id,
        title="Other quiz",
        duration_minutes=10,
        pass_score=50,
        max_attempts=1,
        status="PUBLISHED",
    )
    session.add_all([quiz, draft_quiz, closed_quiz, other_quiz])
    session.commit()

    q_single = Question(
        quiz_id=quiz.id,
        content="Single",
        type="SINGLE_CHOICE",
        options=ADMIN_STYLE_OPTIONS,
        correct_answer=["A"],
        score=10,
        order_no=1,
    )
    q_multi = Question(
        quiz_id=quiz.id,
        content="Multi",
        type="MULTIPLE_CHOICE",
        options=[{"key": "A", "text": "1"}, {"key": "B", "text": "2"}, {"key": "C", "text": "3"}],
        correct_answer=["A", "C"],
        score=10,
        order_no=2,
    )
    # Câu theo định dạng của seed: lựa chọn là chuỗi, đáp án là chuỗi/bool.
    q_seed = Question(
        quiz_id=quiz.id,
        content="Seed style",
        type="SINGLE_CHOICE",
        options=["Review mã", "Xóa repo"],
        correct_answer="Review mã",
        score=10,
        order_no=3,
    )
    q_tf = Question(
        quiz_id=quiz.id,
        content="True false",
        type="TRUE_FALSE",
        options=[True, False],
        correct_answer=True,
        score=10,
        order_no=4,
    )
    session.add_all([q_single, q_multi, q_seed, q_tf])
    session.add(
        Question(
            quiz_id=closed_quiz.id,
            content="Closed q",
            type="SINGLE_CHOICE",
            options=ADMIN_STYLE_OPTIONS,
            correct_answer=["A"],
            score=10,
            order_no=1,
        )
    )
    session.commit()

    internship = Internship(
        name=f"LB {suffix}",
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
        mentor_id=mentor.id,
        roadmap_id=roadmap.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    member_b = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_b.id,
        mentor_id=mentor.id,
        roadmap_id=roadmap.id,
        status=InternshipMemberStatus.ACTIVE,
    )
    member_c = InternshipMember(
        internship_id=internship.id,
        intern_id=intern_c.id,
        mentor_id=mentor.id,
        roadmap_id=None,
        status=InternshipMemberStatus.ACTIVE,
    )
    session.add_all([member_a, member_b, member_c])
    session.commit()

    data = {
        "session": session,
        "admin": admin,
        "mentor": mentor,
        "intern_a": intern_a,
        "intern_b": intern_b,
        "intern_c": intern_c,
        "member_a": member_a,
        "member_b": member_b,
        "roadmap": roadmap,
        "draft_roadmap": draft_roadmap,
        "contents": contents,
        "other_content": other_content,
        "quiz": quiz,
        "draft_quiz": draft_quiz,
        "closed_quiz": closed_quiz,
        "other_quiz": other_quiz,
        "questions": {"single": q_single, "multi": q_multi, "seed": q_seed, "tf": q_tf},
    }
    yield data

    session.rollback()
    session.execute(delete(Internship).where(Internship.id == internship.id))
    session.execute(
        delete(Roadmap).where(Roadmap.id.in_([roadmap.id, other_roadmap.id, draft_roadmap.id]))
    )
    session.execute(
        delete(User).where(
            User.id.in_([admin.id, mentor.id, intern_a.id, intern_b.id, intern_c.id])
        )
    )
    session.commit()
    session.close()


def _h(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def _answers(data: dict, *, single="A", multi=("A", "C"), seed="B", tf="A") -> dict:
    q = data["questions"]
    items = []
    if single is not None:
        items.append({"question_id": str(q["single"].id), "selected_keys": [single]})
    if multi is not None:
        items.append({"question_id": str(q["multi"].id), "selected_keys": list(multi)})
    if seed is not None:
        items.append({"question_id": str(q["seed"].id), "selected_keys": [seed]})
    if tf is not None:
        items.append({"question_id": str(q["tf"].id), "selected_keys": [tf]})
    return {"answers": items}


# ── Phạm vi dữ liệu và phân quyền ───────────────────────────────────────────


def test_roadmap_requires_intern_role(client, learning_data):
    assert client.get("/api/v1/learning/roadmap").status_code == 401
    for user in (learning_data["mentor"], learning_data["admin"]):
        assert client.get("/api/v1/learning/roadmap", headers=_h(user)).status_code == 403


def test_roadmap_view_shows_assigned_roadmap_only(client, learning_data):
    resp = client.get("/api/v1/learning/roadmap", headers=_h(learning_data["intern_a"]))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == str(learning_data["roadmap"].id)
    assert body["total_contents"] == 4
    assert body["completed_contents"] == 0
    assert body["progress_percent"] == 0
    assert [p["name"] for p in body["phases"]] == ["Phase 1", "Phase 2"]
    assert [c["title"] for c in body["phases"][0]["contents"]] == ["C1", "C2"]

    # Chỉ thấy Quiz đã công bố hoặc đã đóng, không thấy Quiz nháp.
    titles = {q["title"] for q in body["phases"][0]["quizzes"]}
    assert titles == {"Quiz 1", "Quiz closed"}
    quiz1 = next(q for q in body["phases"][0]["quizzes"] if q["title"] == "Quiz 1")
    assert quiz1["question_count"] == 4
    assert quiz1["attempts_used"] == 0
    assert quiz1["best_score"] is None


def test_roadmap_errors_when_not_assigned_or_not_active(client, learning_data):
    resp = client.get("/api/v1/learning/roadmap", headers=_h(learning_data["intern_c"]))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ROADMAP_NOT_ASSIGNED"

    session = learning_data["session"]
    member = session.get(InternshipMember, learning_data["member_b"].id)
    member.roadmap_id = learning_data["draft_roadmap"].id
    session.commit()
    resp = client.get("/api/v1/learning/roadmap", headers=_h(learning_data["intern_b"]))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ROADMAP_NOT_AVAILABLE"


def test_content_outside_roadmap_is_404(client, learning_data):
    h = _h(learning_data["intern_a"])
    other = learning_data["other_content"].id
    assert client.get(f"/api/v1/learning/contents/{other}", headers=h).status_code == 404
    assert client.post(f"/api/v1/learning/contents/{other}/start", headers=h).status_code == 404
    assert client.post(f"/api/v1/learning/contents/{other}/complete", headers=h).status_code == 404


# ── Tiến độ do server cập nhật ──────────────────────────────────────────────


def test_content_detail_returns_body(client, learning_data):
    cid = learning_data["contents"][0].id
    resp = client.get(f"/api/v1/learning/contents/{cid}", headers=_h(learning_data["intern_a"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "Body 1"
    assert body["phase_name"] == "Phase 1"
    assert body["status"] == "NOT_STARTED"


def test_start_and_complete_content_update_progress(client, learning_data):
    h = _h(learning_data["intern_a"])
    c1, c2 = learning_data["contents"][0].id, learning_data["contents"][1].id

    started = client.post(f"/api/v1/learning/contents/{c1}/start", headers=h)
    assert started.status_code == 200
    assert started.json()["status"] == "IN_PROGRESS"
    assert started.json()["progress_percent"] == 0

    done = client.post(f"/api/v1/learning/contents/{c1}/complete", headers=h)
    assert done.json()["status"] == "COMPLETED"
    assert done.json()["progress_percent"] == 100
    completed_at = done.json()["completed_at"]
    assert completed_at

    # Gọi lại không đổi kết quả và không hạ trạng thái.
    again = client.post(f"/api/v1/learning/contents/{c1}/complete", headers=h)
    assert again.json()["completed_at"] == completed_at
    restart = client.post(f"/api/v1/learning/contents/{c1}/start", headers=h)
    assert restart.json()["status"] == "COMPLETED"

    # Hoàn thành thẳng một nội dung chưa từng bắt đầu.
    assert client.post(f"/api/v1/learning/contents/{c2}/complete", headers=h).status_code == 200

    body = client.get("/api/v1/learning/roadmap", headers=h).json()
    assert body["completed_contents"] == 2
    assert body["progress_percent"] == 50
    assert body["phases"][0]["progress_percent"] == 100
    assert body["phases"][1]["progress_percent"] == 0


def test_progress_is_per_intern(client, learning_data):
    c1 = learning_data["contents"][0].id
    client.post(f"/api/v1/learning/contents/{c1}/complete", headers=_h(learning_data["intern_a"]))
    body_b = client.get("/api/v1/learning/roadmap", headers=_h(learning_data["intern_b"])).json()
    assert body_b["completed_contents"] == 0
    assert body_b["progress_percent"] == 0


def test_client_cannot_set_progress_directly(client, learning_data):
    c1 = learning_data["contents"][0].id
    h = _h(learning_data["intern_a"])
    resp = client.post(
        f"/api/v1/learning/contents/{c1}/start",
        headers=h,
        json={"status": "COMPLETED", "progress_percent": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"
    assert resp.json()["progress_percent"] == 0


# ── Quiz ────────────────────────────────────────────────────────────────────


def _start(client, data, user_key="intern_a", quiz_key="quiz"):
    return client.post(
        f"/api/v1/learning/quizzes/{data[quiz_key].id}/attempts", headers=_h(data[user_key])
    )


def test_start_attempt_never_leaks_correct_answers(client, learning_data):
    resp = _start(client, learning_data)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["attempt_no"] == 1
    assert body["resumed"] is False
    assert len(body["questions"]) == 4
    assert "correct_answer" not in resp.text
    assert "dap_an_dung" not in resp.text
    first = body["questions"][0]
    assert first["options"] == ADMIN_STYLE_OPTIONS
    # Câu theo định dạng seed được chuẩn hóa thành key A/B.
    seed_q = next(q for q in body["questions"] if q["content"] == "Seed style")
    assert seed_q["options"] == [
        {"key": "A", "text": "Review mã"},
        {"key": "B", "text": "Xóa repo"},
    ]


def test_start_attempt_resumes_open_attempt(client, learning_data):
    first = _start(client, learning_data).json()
    second = _start(client, learning_data).json()
    assert second["attempt_id"] == first["attempt_id"]
    assert second["resumed"] is True


def test_submit_all_correct_and_partially_correct(client, learning_data):
    h = _h(learning_data["intern_a"])
    attempt = _start(client, learning_data).json()
    # Đúng cả bốn câu (seed style: đáp án đúng là lựa chọn A "Review mã").
    resp = client.post(
        f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit",
        headers=h,
        json=_answers(learning_data, seed="A"),
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["score"] == 100
    assert result["passed"] is True
    assert result["earned_points"] == 40
    assert result["total_points"] == 40
    assert all(q["is_correct"] for q in result["questions"])
    assert "correct_answer" not in resp.text

    # Lượt hai: đúng 2/4 → 50 điểm, dưới ngưỡng 60.
    attempt2 = _start(client, learning_data).json()
    assert attempt2["attempt_no"] == 2
    resp2 = client.post(
        f"/api/v1/learning/attempts/{attempt2['attempt_id']}/submit",
        headers=h,
        json=_answers(learning_data, single="B", multi=("A",), seed="A", tf="A"),
    )
    result2 = resp2.json()
    assert result2["score"] == 50
    assert result2["passed"] is False

    results = client.get(
        f"/api/v1/learning/quizzes/{learning_data['quiz'].id}/results", headers=h
    ).json()
    assert results["attempts_used"] == 2
    assert results["best_score"] == 100
    assert results["passed"] is True
    assert [a["score"] for a in results["attempts"]] == [100, 50]


def test_unanswered_questions_score_zero(client, learning_data):
    h = _h(learning_data["intern_a"])
    attempt = _start(client, learning_data).json()
    resp = client.post(
        f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit", headers=h, json={"answers": []}
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 0
    assert resp.json()["passed"] is False


def test_max_attempts_enforced(client, learning_data):
    h = _h(learning_data["intern_a"])
    for _ in range(2):
        attempt = _start(client, learning_data).json()
        client.post(
            f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit",
            headers=h,
            json={"answers": []},
        )
    resp = _start(client, learning_data)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "MAX_ATTEMPTS_REACHED"


def test_submit_twice_and_invalid_answers_rejected(client, learning_data):
    h = _h(learning_data["intern_a"])
    attempt = _start(client, learning_data).json()
    url = f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit"
    q = learning_data["questions"]

    bad_key = client.post(
        url,
        headers=h,
        json={"answers": [{"question_id": str(q["single"].id), "selected_keys": ["Z"]}]},
    )
    assert bad_key.status_code == 422
    two_for_single = client.post(
        url,
        headers=h,
        json={"answers": [{"question_id": str(q["single"].id), "selected_keys": ["A", "B"]}]},
    )
    assert two_for_single.status_code == 422
    foreign_question = client.post(
        url,
        headers=h,
        json={"answers": [{"question_id": str(uuid.uuid4()), "selected_keys": ["A"]}]},
    )
    assert foreign_question.status_code == 422
    duplicate = client.post(
        url,
        headers=h,
        json={
            "answers": [
                {"question_id": str(q["single"].id), "selected_keys": ["A"]},
                {"question_id": str(q["single"].id), "selected_keys": ["B"]},
            ]
        },
    )
    assert duplicate.status_code == 422

    # Lỗi validate không làm mất lượt làm; nộp hợp lệ vẫn được, nộp lần hai thì bị chặn.
    assert client.post(url, headers=h, json=_answers(learning_data)).status_code == 200
    again = client.post(url, headers=h, json=_answers(learning_data))
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ATTEMPT_ALREADY_SUBMITTED"


def test_other_intern_cannot_submit_or_see_attempt(client, learning_data):
    attempt = _start(client, learning_data).json()
    resp = client.post(
        f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit",
        headers=_h(learning_data["intern_b"]),
        json=_answers(learning_data),
    )
    assert resp.status_code == 404
    results_b = client.get(
        f"/api/v1/learning/quizzes/{learning_data['quiz'].id}/results",
        headers=_h(learning_data["intern_b"]),
    ).json()
    assert results_b["attempts_used"] == 0


def test_quiz_scope_and_status_rules(client, learning_data):
    for key in ("draft_quiz", "other_quiz"):
        assert _start(client, learning_data, quiz_key=key).status_code == 404
    closed = _start(client, learning_data, quiz_key="closed_quiz")
    assert closed.status_code == 409
    assert closed.json()["error"]["code"] == "QUIZ_NOT_AVAILABLE"
    draft_results = client.get(
        f"/api/v1/learning/quizzes/{learning_data['draft_quiz'].id}/results",
        headers=_h(learning_data["intern_a"]),
    )
    assert draft_results.status_code == 404


def test_expired_open_attempt_is_closed_with_zero(client, learning_data):
    h = _h(learning_data["intern_a"])
    attempt = _start(client, learning_data).json()

    session = learning_data["session"]
    row = session.get(QuizAttempt, uuid.UUID(attempt["attempt_id"]))
    row.started_at = datetime.now(UTC) - timedelta(hours=2)
    session.commit()

    # Nộp quá hạn: bị từ chối và tính 0 điểm.
    resp = client.post(
        f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit",
        headers=h,
        json=_answers(learning_data),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ATTEMPT_EXPIRED"

    results = client.get(
        f"/api/v1/learning/quizzes/{learning_data['quiz'].id}/results", headers=h
    ).json()
    assert results["attempts"][0]["status"] == "SUBMITTED"
    assert results["attempts"][0]["score"] == 0
    assert results["attempts"][0]["passed"] is False

    # Lượt quá hạn vẫn tính là đã dùng một lần; còn lượt thứ hai.
    nxt = _start(client, learning_data)
    assert nxt.status_code == 200
    assert nxt.json()["attempt_no"] == 2


def test_expired_unsubmitted_attempt_closed_when_starting_again(client, learning_data):
    h = _h(learning_data["intern_a"])
    attempt = _start(client, learning_data).json()
    session = learning_data["session"]
    row = session.get(QuizAttempt, uuid.UUID(attempt["attempt_id"]))
    row.started_at = datetime.now(UTC) - timedelta(hours=2)
    session.commit()

    new_attempt = _start(client, learning_data)
    assert new_attempt.status_code == 200
    assert new_attempt.json()["attempt_no"] == 2
    assert new_attempt.json()["resumed"] is False
    results = client.get(
        f"/api/v1/learning/quizzes/{learning_data['quiz'].id}/results", headers=h
    ).json()
    assert results["attempts"][0]["score"] == 0


def test_text_question_graded_and_ungradable_excluded(client, learning_data):
    session = learning_data["session"]
    quiz = Quiz(
        phase_id=learning_data["contents"][0].phase_id,
        title="Text quiz",
        duration_minutes=10,
        pass_score=50,
        max_attempts=3,
        status="PUBLISHED",
    )
    session.add(quiz)
    session.commit()
    graded = Question(
        quiz_id=quiz.id,
        content="Thủ đô?",
        type="TEXT",
        options=None,
        correct_answer=["Hà Nội"],
        score=10,
        order_no=1,
    )
    ungradable = Question(
        quiz_id=quiz.id,
        content="Ý kiến của bạn?",
        type="TEXT",
        options=None,
        correct_answer=[""],
        score=10,
        order_no=2,
    )
    session.add_all([graded, ungradable])
    session.commit()

    h = _h(learning_data["intern_a"])
    attempt = client.post(f"/api/v1/learning/quizzes/{quiz.id}/attempts", headers=h).json()
    resp = client.post(
        f"/api/v1/learning/attempts/{attempt['attempt_id']}/submit",
        headers=h,
        json={
            "answers": [
                {"question_id": str(graded.id), "text": "  hà   nội "},
                {"question_id": str(ungradable.id), "text": "tuỳ"},
            ]
        },
    )
    result = resp.json()
    assert resp.status_code == 200, resp.text
    assert result["score"] == 100
    assert result["total_points"] == 10
    assert result["ungraded_questions"] == 1
    assert result["passed"] is True


def test_seed_attempts_do_not_break_results(client, learning_data):
    """Lượt làm cũ do seed tạo có answers dạng danh sách chuỗi vẫn phải đọc được."""
    session = learning_data["session"]
    session.add(
        QuizAttempt(
            quiz_id=learning_data["quiz"].id,
            internship_member_id=learning_data["member_a"].id,
            attempt_no=1,
            answers=["git branch", "Review mã", True],
            score=90,
            passed=True,
            started_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )
    )
    session.commit()
    h = _h(learning_data["intern_a"])
    results = client.get(
        f"/api/v1/learning/quizzes/{learning_data['quiz'].id}/results", headers=h
    ).json()
    assert results["best_score"] == 90
    roadmap = client.get("/api/v1/learning/roadmap", headers=h).json()
    quiz = next(q for q in roadmap["phases"][0]["quizzes"] if q["title"] == "Quiz 1")
    assert quiz["attempts_used"] == 1
    assert quiz["passed"] is True
    # Lượt tiếp theo mang số 2 và còn dùng được (max_attempts = 2).
    assert _start(client, learning_data).json()["attempt_no"] == 2


def test_learning_progress_rows_removed_with_member(learning_data):
    """Dọn dữ liệu fixture không để lại tiến độ mồ côi."""
    session = learning_data["session"]
    session.add(
        LearningProgress(
            internship_member_id=learning_data["member_a"].id,
            content_id=learning_data["contents"][0].id,
            status="IN_PROGRESS",
            progress_percent=10,
        )
    )
    session.commit()
