"""Nghiệp vụ UC-6: Intern học tập, theo dõi tiến độ và làm Quiz.

Nguyên tắc (docs/s0-01-api-access-control.md, mục 6):
- Phạm vi dữ liệu do server suy ra từ Intern đang đăng nhập, không nhận ID Intern từ client.
- Dữ liệu ngoài phạm vi (lộ trình khác, Quiz nháp, lượt làm bài của người khác) trả 404.
- Client không được sửa trực tiếp phần trăm hoặc trạng thái tiến độ.
- Chấm điểm Quiz ở server; đáp án đúng không bao giờ được gửi cho Intern.
"""

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import (
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
from app.models.enums import InternshipMemberStatus
from app.schemas.learning import (
    AnswerSubmit,
    AttemptResultRead,
    AttemptStartedRead,
    AttemptSubmit,
    AttemptSummary,
    LearningContentDetail,
    LearningContentItem,
    LearningPhaseItem,
    LearningProgressRead,
    LearningQuizSummary,
    LearningRoadmapRead,
    QuestionResult,
    QuizQuestionPublic,
    QuizResultsRead,
)

ACTIVE_MEMBER_STATUSES = (
    InternshipMemberStatus.ACTIVE.value,
    InternshipMemberStatus.EXTENDED.value,
)
VISIBLE_QUIZ_STATUSES = ("PUBLISHED", "CLOSED")
CHOICE_TYPES = ("SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE")
SINGLE_ANSWER_TYPES = ("SINGLE_CHOICE", "TRUE_FALSE")
# Cho phép nộp trễ một chút so với hạn để bù độ trễ mạng.
SUBMIT_GRACE = timedelta(seconds=60)


# ---------------------------------------------------------------------------
# Chuẩn hóa lựa chọn và đáp án
#
# Dữ liệu câu hỏi trong hệ thống có hai dạng cùng tồn tại:
#   * Giao diện Admin: options = [{"key": "A", "text": "..."}], correct_answer = ["A"]
#   * Dữ liệu seed:    options = ["git branch", ...],          correct_answer = "git branch"
#                      TRUE_FALSE: options = [True, False],     correct_answer = True
# Các hàm dưới đây đưa cả hai về cùng một dạng để chấm điểm.
# ---------------------------------------------------------------------------


def _letter_key(index: int) -> str:
    return chr(ord("A") + index) if index < 26 else f"OPT{index + 1}"


def _bool_text(value: bool) -> str:
    return "Đúng" if value else "Sai"


def normalize_options(raw: Any, question_type: str) -> list[dict[str, str]]:
    """Trả danh sách lựa chọn dạng [{"key", "text"}]; câu TEXT không có lựa chọn."""
    if question_type == "TEXT":
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = None

    items: list[tuple[str | None, Any]] = []
    if isinstance(raw, dict):
        items = [(str(key), value) for key, value in raw.items()]
    elif isinstance(raw, list):
        items = [(None, value) for value in raw]

    options: list[dict[str, str]] = []
    for index, (mapped_key, value) in enumerate(items):
        if isinstance(value, dict) and "key" in value:
            key = str(value["key"]).strip()
            text = str(value.get("text", ""))
        else:
            key = mapped_key or _letter_key(index)
            text = _bool_text(value) if isinstance(value, bool) else str(value)
        options.append({"key": key, "text": text})

    if not options and question_type == "TRUE_FALSE":
        options = [{"key": "A", "text": "Đúng"}, {"key": "B", "text": "Sai"}]
    return options


def _bool_key(options: list[dict[str, str]], value: bool) -> str | None:
    wanted = _bool_text(value).casefold()
    for option in options:
        if option["text"].strip().casefold() == wanted:
            return option["key"]
    index = 0 if value else 1
    return options[index]["key"] if len(options) > index else None


def _match_option(value: Any, options: list[dict[str, str]], question_type: str) -> str | None:
    if isinstance(value, bool):
        return _bool_key(options, value)
    text = str(value).strip()
    if not text:
        return None
    folded = text.casefold()
    for option in options:
        if option["key"].casefold() == folded:
            return option["key"]
    for option in options:
        if option["text"].strip().casefold() == folded:
            return option["key"]
    if question_type == "TRUE_FALSE":
        if folded in {"true", "đúng"}:
            return _bool_key(options, True)
        if folded in {"false", "sai"}:
            return _bool_key(options, False)
    return None


def _as_values(raw: Any) -> list[Any]:
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith(("[", "{")):
            try:
                raw = json.loads(stripped)
            except ValueError:
                pass
    return raw if isinstance(raw, list) else [raw]


def correct_keys(raw: Any, options: list[dict[str, str]], question_type: str) -> set[str]:
    """Tập key của các lựa chọn đúng (rỗng nếu dữ liệu đáp án không dùng được)."""
    canonical = {option["key"].casefold(): option["key"] for option in options}
    found: set[str] = set()
    for value in _as_values(raw):
        if value is None:
            continue
        if isinstance(value, dict):
            if "key" in value:
                found.add(str(value["key"]).strip())
            keys = value.get("keys")
            if isinstance(keys, list):
                found.update(str(key).strip() for key in keys)
            continue
        key = _match_option(value, options, question_type)
        if key is not None:
            found.add(key)
    return {canonical[key.casefold()] for key in found if key.casefold() in canonical}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def accepted_text_answers(raw: Any) -> set[str]:
    accepted: set[str] = set()
    for value in _as_values(raw):
        if isinstance(value, str | int | float) and not isinstance(value, bool):
            normalized = normalize_text(str(value))
            if normalized:
                accepted.add(normalized)
    return accepted


def grade_question(
    question_type: str,
    options: list[dict[str, str]],
    correct_answer: Any,
    selected_keys: list[str],
    text: str | None,
) -> bool | None:
    """Chấm một câu. Trả None nếu câu hỏi chưa có đáp án dùng được để chấm tự động."""
    if question_type == "TEXT":
        accepted = accepted_text_answers(correct_answer)
        if not accepted:
            return None
        return normalize_text(text or "") in accepted

    correct = correct_keys(correct_answer, options, question_type)
    if not correct:
        return None
    selected = set(selected_keys)
    if question_type in SINGLE_ANSWER_TYPES:
        return len(selected) == 1 and selected <= correct
    return selected == correct


def _percent(value: Decimal | float | int | None) -> float:
    return round(float(value or 0), 1)


def _now() -> datetime:
    return datetime.now(UTC)


class LearningService:
    # ------------------------------------------------------------------
    # Phạm vi dữ liệu
    # ------------------------------------------------------------------

    @staticmethod
    def get_current_member(db: Session, user: User) -> InternshipMember:
        member = db.scalar(
            select(InternshipMember)
            .where(
                InternshipMember.intern_id == user.id,
                InternshipMember.status.in_(ACTIVE_MEMBER_STATUSES),
            )
            .order_by(InternshipMember.created_at.desc())
            .limit(1)
        )
        if member is None:
            raise ApiError(
                404, "INTERNSHIP_NOT_FOUND", "Bạn chưa tham gia đợt thực tập nào đang hoạt động."
            )
        return member

    @staticmethod
    def _get_scope(db: Session, user: User) -> tuple[InternshipMember, Roadmap]:
        member = LearningService.get_current_member(db, user)
        if member.roadmap_id is None:
            raise ApiError(404, "ROADMAP_NOT_ASSIGNED", "Bạn chưa được giao lộ trình đào tạo.")
        roadmap = db.get(Roadmap, member.roadmap_id)
        if roadmap is None or roadmap.status != "ACTIVE":
            raise ApiError(404, "ROADMAP_NOT_AVAILABLE", "Lộ trình đào tạo hiện chưa khả dụng.")
        return member, roadmap

    @staticmethod
    def _scoped_content(
        db: Session, roadmap: Roadmap, content_id: uuid.UUID
    ) -> tuple[LearningContent, Phase]:
        row = db.execute(
            select(LearningContent, Phase)
            .join(Phase, Phase.id == LearningContent.phase_id)
            .where(LearningContent.id == content_id, Phase.roadmap_id == roadmap.id)
        ).first()
        if row is None:
            raise ApiError(404, "CONTENT_NOT_FOUND", "Không tìm thấy nội dung đào tạo.")
        return row[0], row[1]

    @staticmethod
    def _scoped_quiz(db: Session, roadmap: Roadmap, quiz_id: uuid.UUID) -> Quiz:
        quiz = db.scalar(
            select(Quiz)
            .join(Phase, Phase.id == Quiz.phase_id)
            .where(
                Quiz.id == quiz_id,
                Phase.roadmap_id == roadmap.id,
                Quiz.status.in_(VISIBLE_QUIZ_STATUSES),
            )
        )
        if quiz is None:
            raise ApiError(404, "QUIZ_NOT_FOUND", "Không tìm thấy bài kiểm tra.")
        return quiz

    # ------------------------------------------------------------------
    # Lộ trình và nội dung
    # ------------------------------------------------------------------

    @staticmethod
    def get_roadmap(db: Session, user: User) -> LearningRoadmapRead:
        member, roadmap = LearningService._get_scope(db, user)

        phases = list(
            db.scalars(
                select(Phase).where(Phase.roadmap_id == roadmap.id).order_by(Phase.order_no.asc())
            )
        )
        phase_ids = [phase.id for phase in phases]

        contents: list[LearningContent] = []
        quizzes: list[Quiz] = []
        if phase_ids:
            contents = list(
                db.scalars(
                    select(LearningContent)
                    .where(LearningContent.phase_id.in_(phase_ids))
                    .order_by(LearningContent.order_no.asc())
                )
            )
            quizzes = list(
                db.scalars(
                    select(Quiz)
                    .where(Quiz.phase_id.in_(phase_ids), Quiz.status.in_(VISIBLE_QUIZ_STATUSES))
                    .order_by(Quiz.created_at.asc())
                )
            )

        progress_by_content: dict[uuid.UUID, LearningProgress] = {}
        if contents:
            progress_by_content = {
                row.content_id: row
                for row in db.scalars(
                    select(LearningProgress).where(
                        LearningProgress.internship_member_id == member.id,
                        LearningProgress.content_id.in_([content.id for content in contents]),
                    )
                )
            }

        question_counts: dict[uuid.UUID, int] = {}
        attempts_by_quiz: dict[uuid.UUID, list[QuizAttempt]] = {}
        if quizzes:
            quiz_ids = [quiz.id for quiz in quizzes]
            question_counts = {
                quiz_id: count
                for quiz_id, count in db.execute(
                    select(Question.quiz_id, func.count(Question.id))
                    .where(Question.quiz_id.in_(quiz_ids))
                    .group_by(Question.quiz_id)
                )
            }
            for attempt in db.scalars(
                select(QuizAttempt).where(
                    QuizAttempt.internship_member_id == member.id,
                    QuizAttempt.quiz_id.in_(quiz_ids),
                )
            ):
                attempts_by_quiz.setdefault(attempt.quiz_id, []).append(attempt)

        phase_items: list[LearningPhaseItem] = []
        total_contents = 0
        completed_contents = 0
        percent_sum = 0.0
        for phase in phases:
            content_items: list[LearningContentItem] = []
            phase_percent_sum = 0.0
            phase_completed = 0
            for content in (c for c in contents if c.phase_id == phase.id):
                progress = progress_by_content.get(content.id)
                percent = _percent(progress.progress_percent) if progress else 0.0
                status = progress.status if progress else "NOT_STARTED"
                content_items.append(
                    LearningContentItem(
                        id=content.id,
                        title=content.title,
                        description=content.description,
                        type=content.type,
                        resource_url=content.resource_url,
                        order_no=content.order_no,
                        status=status,
                        progress_percent=percent,
                        completed_at=progress.completed_at if progress else None,
                    )
                )
                phase_percent_sum += percent
                phase_completed += 1 if status == "COMPLETED" else 0

            quiz_items = [
                LearningService._quiz_summary(
                    quiz, question_counts.get(quiz.id, 0), attempts_by_quiz.get(quiz.id, [])
                )
                for quiz in quizzes
                if quiz.phase_id == phase.id
            ]
            count = len(content_items)
            phase_items.append(
                LearningPhaseItem(
                    id=phase.id,
                    name=phase.name,
                    description=phase.description,
                    order_no=phase.order_no,
                    progress_percent=round(phase_percent_sum / count, 1) if count else 0.0,
                    completed_contents=phase_completed,
                    total_contents=count,
                    contents=content_items,
                    quizzes=quiz_items,
                )
            )
            total_contents += count
            completed_contents += phase_completed
            percent_sum += phase_percent_sum

        return LearningRoadmapRead(
            id=roadmap.id,
            name=roadmap.name,
            description=roadmap.description,
            progress_percent=round(percent_sum / total_contents, 1) if total_contents else 0.0,
            completed_contents=completed_contents,
            total_contents=total_contents,
            phases=phase_items,
        )

    @staticmethod
    def _quiz_summary(
        quiz: Quiz, question_count: int, attempts: list[QuizAttempt]
    ) -> LearningQuizSummary:
        scores = [float(a.score) for a in attempts if a.submitted_at and a.score is not None]
        return LearningQuizSummary(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            duration_minutes=quiz.duration_minutes,
            pass_score=float(quiz.pass_score),
            max_attempts=quiz.max_attempts,
            status=quiz.status,
            question_count=question_count,
            attempts_used=len(attempts),
            best_score=max(scores) if scores else None,
            passed=any(a.passed for a in attempts),
        )

    @staticmethod
    def get_content(db: Session, user: User, content_id: uuid.UUID) -> LearningContentDetail:
        member, roadmap = LearningService._get_scope(db, user)
        content, phase = LearningService._scoped_content(db, roadmap, content_id)
        progress = db.scalar(
            select(LearningProgress).where(
                LearningProgress.internship_member_id == member.id,
                LearningProgress.content_id == content.id,
            )
        )
        return LearningContentDetail(
            id=content.id,
            title=content.title,
            description=content.description,
            type=content.type,
            resource_url=content.resource_url,
            order_no=content.order_no,
            status=progress.status if progress else "NOT_STARTED",
            progress_percent=_percent(progress.progress_percent) if progress else 0.0,
            completed_at=progress.completed_at if progress else None,
            phase_id=phase.id,
            phase_name=phase.name,
            content=content.content,
        )

    @staticmethod
    def _get_or_create_progress(
        db: Session, member: InternshipMember, content: LearningContent
    ) -> LearningProgress:
        query = select(LearningProgress).where(
            LearningProgress.internship_member_id == member.id,
            LearningProgress.content_id == content.id,
        )
        progress = db.scalar(query)
        if progress is not None:
            return progress
        try:
            with db.begin_nested():
                progress = LearningProgress(
                    internship_member_id=member.id,
                    content_id=content.id,
                    status="NOT_STARTED",
                    progress_percent=0,
                )
                db.add(progress)
                db.flush()
        except IntegrityError:
            # Hai request cùng tạo dòng tiến độ: dùng dòng của request thắng.
            progress = db.scalar(query)
            if progress is None:
                raise
        return progress

    @staticmethod
    def start_content(db: Session, user: User, content_id: uuid.UUID) -> LearningProgressRead:
        """Ghi nhận sự kiện bắt đầu học. Không bao giờ hạ trạng thái đã hoàn thành."""
        member, roadmap = LearningService._get_scope(db, user)
        content, _ = LearningService._scoped_content(db, roadmap, content_id)
        progress = LearningService._get_or_create_progress(db, member, content)
        if progress.status == "NOT_STARTED":
            progress.status = "IN_PROGRESS"
            progress.updated_at = _now()
        db.commit()
        return LearningService._progress_read(progress)

    @staticmethod
    def complete_content(db: Session, user: User, content_id: uuid.UUID) -> LearningProgressRead:
        """Ghi nhận sự kiện hoàn thành nội dung. Gọi lặp lại không đổi kết quả."""
        member, roadmap = LearningService._get_scope(db, user)
        content, _ = LearningService._scoped_content(db, roadmap, content_id)
        progress = LearningService._get_or_create_progress(db, member, content)
        if progress.status != "COMPLETED":
            now = _now()
            progress.status = "COMPLETED"
            progress.progress_percent = 100
            progress.completed_at = now
            progress.updated_at = now
        db.commit()
        return LearningService._progress_read(progress)

    @staticmethod
    def _progress_read(progress: LearningProgress) -> LearningProgressRead:
        return LearningProgressRead(
            content_id=progress.content_id,
            status=progress.status,
            progress_percent=_percent(progress.progress_percent),
            completed_at=progress.completed_at,
        )

    # ------------------------------------------------------------------
    # Quiz
    # ------------------------------------------------------------------

    @staticmethod
    def _quiz_questions(db: Session, quiz_id: uuid.UUID) -> list[Question]:
        return list(
            db.scalars(
                select(Question)
                .where(Question.quiz_id == quiz_id)
                .order_by(Question.order_no.asc().nulls_last(), Question.created_at.asc())
            )
        )

    @staticmethod
    def _expires_at(attempt: QuizAttempt, quiz: Quiz) -> datetime:
        return attempt.started_at + timedelta(minutes=quiz.duration_minutes)

    @staticmethod
    def _close_as_timed_out(attempt: QuizAttempt, quiz: Quiz) -> None:
        attempt.answers = []
        attempt.score = 0
        attempt.passed = False
        attempt.submitted_at = LearningService._expires_at(attempt, quiz)

    @staticmethod
    def start_attempt(db: Session, user: User, quiz_id: uuid.UUID) -> AttemptStartedRead:
        """Bắt đầu một lượt làm bài, hoặc tiếp tục lượt đang làm dở còn thời gian."""
        for retry in range(2):
            try:
                return LearningService._start_attempt_once(db, user, quiz_id)
            except IntegrityError:
                # Hai request cùng tạo lượt mới (trùng số lần làm): thử lại một lần.
                db.rollback()
                if retry == 1:
                    raise ApiError(
                        409, "ATTEMPT_CONFLICT", "Không thể bắt đầu bài làm, vui lòng thử lại."
                    ) from None
        raise AssertionError("unreachable")

    @staticmethod
    def _start_attempt_once(db: Session, user: User, quiz_id: uuid.UUID) -> AttemptStartedRead:
        member, roadmap = LearningService._get_scope(db, user)
        quiz = LearningService._scoped_quiz(db, roadmap, quiz_id)
        if quiz.status != "PUBLISHED":
            raise ApiError(409, "QUIZ_NOT_AVAILABLE", "Bài kiểm tra này đã đóng.")
        questions = LearningService._quiz_questions(db, quiz.id)
        if not questions:
            raise ApiError(409, "QUIZ_HAS_NO_QUESTIONS", "Bài kiểm tra chưa có câu hỏi.")

        attempts = list(
            db.scalars(
                select(QuizAttempt)
                .where(
                    QuizAttempt.quiz_id == quiz.id,
                    QuizAttempt.internship_member_id == member.id,
                )
                .order_by(QuizAttempt.attempt_no.asc())
            )
        )
        now = _now()
        open_attempt = next((a for a in attempts if a.submitted_at is None), None)
        if open_attempt is not None:
            expires_at = LearningService._expires_at(open_attempt, quiz)
            if now <= expires_at:
                return LearningService._attempt_started(open_attempt, quiz, questions, True)
            # Lượt cũ đã quá hạn mà chưa nộp: đóng với 0 điểm, vẫn tính là đã dùng một lần.
            LearningService._close_as_timed_out(open_attempt, quiz)
            db.flush()

        if len(attempts) >= quiz.max_attempts:
            db.commit()
            raise ApiError(
                409,
                "MAX_ATTEMPTS_REACHED",
                "Bạn đã dùng hết số lần làm bài cho phép.",
                {"max_attempts": quiz.max_attempts},
            )

        attempt = QuizAttempt(
            quiz_id=quiz.id,
            internship_member_id=member.id,
            attempt_no=max((a.attempt_no for a in attempts), default=0) + 1,
            answers=None,
            started_at=now,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return LearningService._attempt_started(attempt, quiz, questions, False)

    @staticmethod
    def _attempt_started(
        attempt: QuizAttempt, quiz: Quiz, questions: list[Question], resumed: bool
    ) -> AttemptStartedRead:
        return AttemptStartedRead(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            attempt_no=attempt.attempt_no,
            started_at=attempt.started_at,
            expires_at=LearningService._expires_at(attempt, quiz),
            duration_minutes=quiz.duration_minutes,
            resumed=resumed,
            questions=[
                QuizQuestionPublic(
                    id=question.id,
                    content=question.content,
                    type=question.type,
                    options=normalize_options(question.options, question.type),
                    score=float(question.score),
                    order_no=question.order_no,
                )
                for question in questions
            ],
        )

    @staticmethod
    def submit_attempt(
        db: Session, user: User, attempt_id: uuid.UUID, payload: AttemptSubmit
    ) -> AttemptResultRead:
        member = LearningService.get_current_member(db, user)
        attempt = db.get(QuizAttempt, attempt_id)
        if attempt is None or attempt.internship_member_id != member.id:
            raise ApiError(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
        if attempt.submitted_at is not None:
            raise ApiError(409, "ATTEMPT_ALREADY_SUBMITTED", "Lượt làm bài này đã được nộp.")

        quiz = db.get(Quiz, attempt.quiz_id)
        if quiz is None:
            raise ApiError(404, "QUIZ_NOT_FOUND", "Không tìm thấy bài kiểm tra.")

        now = _now()
        if now > LearningService._expires_at(attempt, quiz) + SUBMIT_GRACE:
            LearningService._close_as_timed_out(attempt, quiz)
            db.commit()
            raise ApiError(
                409,
                "ATTEMPT_EXPIRED",
                "Đã hết thời gian làm bài, lượt làm này được tính 0 điểm.",
                {"attempt_id": str(attempt.id), "score": 0},
            )

        questions = LearningService._quiz_questions(db, quiz.id)
        answers = LearningService._validate_answers(questions, payload.answers)

        results: list[QuestionResult] = []
        earned_total = 0.0
        possible_total = 0.0
        ungraded = 0
        for question in questions:
            options = normalize_options(question.options, question.type)
            answer = answers.get(question.id)
            outcome = grade_question(
                question.type,
                options,
                question.correct_answer,
                answer[0] if answer else [],
                answer[1] if answer else None,
            )
            points = float(question.score)
            if outcome is None:
                ungraded += 1
                results.append(QuestionResult(question_id=question.id, is_correct=None))
                continue
            possible_total += points
            earned = points if outcome else 0.0
            earned_total += earned
            results.append(
                QuestionResult(question_id=question.id, is_correct=outcome, earned_score=earned)
            )

        score = round(earned_total / possible_total * 100, 2) if possible_total > 0 else 0.0
        passed = possible_total > 0 and score >= float(quiz.pass_score)

        attempt.answers = [
            {
                "question_id": str(question_id),
                "selected_keys": keys,
                "text": text,
            }
            for question_id, (keys, text) in answers.items()
        ]
        attempt.score = score
        attempt.passed = passed
        attempt.submitted_at = now
        db.commit()

        return AttemptResultRead(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            attempt_no=attempt.attempt_no,
            score=score,
            passed=passed,
            earned_points=earned_total,
            total_points=possible_total,
            ungraded_questions=ungraded,
            started_at=attempt.started_at,
            submitted_at=now,
            questions=results,
        )

    @staticmethod
    def _validate_answers(
        questions: list[Question], submitted: list[AnswerSubmit]
    ) -> dict[uuid.UUID, tuple[list[str], str | None]]:
        """Kiểm tra bài nộp và trả {question_id: (key đã chọn, nội dung tự luận)}."""
        by_id = {question.id: question for question in questions}
        cleaned: dict[uuid.UUID, tuple[list[str], str | None]] = {}
        for answer in submitted:
            question = by_id.get(answer.question_id)
            if question is None:
                raise ApiError(
                    422,
                    "INVALID_ANSWER",
                    "Có câu trả lời không thuộc bài kiểm tra này.",
                    {"question_id": str(answer.question_id)},
                )
            if answer.question_id in cleaned:
                raise ApiError(
                    422,
                    "DUPLICATE_ANSWER",
                    "Mỗi câu hỏi chỉ được trả lời một lần.",
                    {"question_id": str(answer.question_id)},
                )

            if question.type in CHOICE_TYPES:
                options = normalize_options(question.options, question.type)
                canonical = {option["key"].casefold(): option["key"] for option in options}
                keys: list[str] = []
                for raw_key in answer.selected_keys:
                    key = canonical.get(raw_key.strip().casefold())
                    if key is None:
                        raise ApiError(
                            422,
                            "INVALID_ANSWER",
                            "Lựa chọn không hợp lệ.",
                            {"question_id": str(question.id), "key": raw_key},
                        )
                    if key not in keys:
                        keys.append(key)
                if question.type in SINGLE_ANSWER_TYPES and len(keys) > 1:
                    raise ApiError(
                        422,
                        "INVALID_ANSWER",
                        "Câu hỏi này chỉ được chọn một đáp án.",
                        {"question_id": str(question.id)},
                    )
                cleaned[question.id] = (keys, None)
            else:
                text = (answer.text or "").strip()
                cleaned[question.id] = ([], text or None)
        return cleaned

    @staticmethod
    def get_quiz_results(db: Session, user: User, quiz_id: uuid.UUID) -> QuizResultsRead:
        member, roadmap = LearningService._get_scope(db, user)
        quiz = LearningService._scoped_quiz(db, roadmap, quiz_id)
        attempts = list(
            db.scalars(
                select(QuizAttempt)
                .where(
                    QuizAttempt.quiz_id == quiz.id,
                    QuizAttempt.internship_member_id == member.id,
                )
                .order_by(QuizAttempt.attempt_no.asc())
            )
        )
        scores = [float(a.score) for a in attempts if a.submitted_at and a.score is not None]
        return QuizResultsRead(
            quiz_id=quiz.id,
            title=quiz.title,
            pass_score=float(quiz.pass_score),
            max_attempts=quiz.max_attempts,
            attempts_used=len(attempts),
            best_score=max(scores) if scores else None,
            passed=any(a.passed for a in attempts),
            attempts=[
                AttemptSummary(
                    attempt_id=a.id,
                    attempt_no=a.attempt_no,
                    status="SUBMITTED" if a.submitted_at else "IN_PROGRESS",
                    score=float(a.score) if a.score is not None else None,
                    passed=a.passed,
                    started_at=a.started_at,
                    submitted_at=a.submitted_at,
                )
                for a in attempts
            ],
        )
