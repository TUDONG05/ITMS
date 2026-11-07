"""Nghiệp vụ UC-12: Quản lý đánh giá.

Loại đánh giá: WEEKLY (nhận xét tuần), PERIODIC (định kỳ), FINAL (cuối cùng, Đạt/Chưa đạt).

Quy định (docs/s0-01-api-access-control.md, mục 4 và 6):
- Admin quản lý tiêu chí/thang điểm/trọng số; chỉ được ĐỌC đánh giá (kể cả nháp) để giám sát,
  không sửa hay công bố.
- Mentor chỉ lập, sửa nháp và công bố đánh giá của Intern mình phụ trách.
- Intern chỉ thấy đánh giá đã công bố của chính mình; bản nháp trả 404.
- Dữ liệu ngoài phạm vi trả 404, không trả 403.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import (
    Evaluation,
    EvaluationCriterion,
    Internship,
    InternshipMember,
    User,
)
from app.models.enums import UserRole
from app.schemas.evaluation import (
    CriterionCreate,
    CriterionListRead,
    CriterionRead,
    CriterionUpdate,
    EvaluationCreate,
    EvaluationRead,
    EvaluationUpdate,
    ScoreInput,
    ScoreRead,
)

TOTAL_SCALE = 10  # Tổng điểm luôn quy về thang 10.
WEEKLY_MAX_DAYS = 14  # Một nhận xét tuần không dài quá số ngày này.


def _now() -> datetime:
    return datetime.now(UTC)


def _f(value: Any) -> float:
    return float(value) if value is not None else 0.0


def compute_total(items: list[dict[str, Any]]) -> float:
    """Tổng điểm thang 10, bình quân theo trọng số.

    tổng = Σ(điểm / điểm tối đa × trọng số) / Σ trọng số × 10
    Ví dụ dữ liệu mẫu: (8,5×40 + 9×30 + 9×30) / 100 = 8,8.
    Nếu mọi trọng số bằng 0 thì lấy trung bình cộng tỷ lệ điểm.
    """
    if not items:
        return 0.0
    weight_sum = sum(item["weight"] for item in items)
    if weight_sum > 0:
        ratio = sum(item["score"] / item["max_score"] * item["weight"] for item in items)
        return round(ratio / weight_sum * TOTAL_SCALE, 2)
    ratio = sum(item["score"] / item["max_score"] for item in items)
    return round(ratio / len(items) * TOTAL_SCALE, 2)


class EvaluationService:
    # ------------------------------------------------------------------
    # Tiêu chí đánh giá
    # ------------------------------------------------------------------

    @staticmethod
    def _criterion_read(criterion: EvaluationCriterion) -> CriterionRead:
        return CriterionRead(
            id=criterion.id,
            name=criterion.name,
            description=criterion.description,
            max_score=_f(criterion.max_score),
            weight=_f(criterion.weight),
            status=criterion.status,
            created_at=criterion.created_at,
            updated_at=criterion.updated_at,
        )

    @staticmethod
    def list_criteria(db: Session, user: User, status: str | None = None) -> CriterionListRead:
        query = select(EvaluationCriterion).order_by(
            EvaluationCriterion.created_at.asc(), EvaluationCriterion.name.asc()
        )
        if user.role == UserRole.ADMIN:
            if status in ("ACTIVE", "INACTIVE"):
                query = query.where(EvaluationCriterion.status == status)
        else:
            # Mentor chỉ cần các tiêu chí đang áp dụng để chấm điểm.
            query = query.where(EvaluationCriterion.status == "ACTIVE")
        rows = list(db.scalars(query))
        active_weight = db.scalar(
            select(func.coalesce(func.sum(EvaluationCriterion.weight), 0)).where(
                EvaluationCriterion.status == "ACTIVE"
            )
        )
        return CriterionListRead(
            items=[EvaluationService._criterion_read(row) for row in rows],
            total_active_weight=round(_f(active_weight), 2),
        )

    @staticmethod
    def _ensure_unique_name(db: Session, name: str, exclude_id: uuid.UUID | None = None) -> None:
        query = select(EvaluationCriterion.id).where(
            func.lower(EvaluationCriterion.name) == name.lower()
        )
        if exclude_id is not None:
            query = query.where(EvaluationCriterion.id != exclude_id)
        if db.scalar(query) is not None:
            raise ApiError(409, "CRITERION_NAME_EXISTS", "Tên tiêu chí đã tồn tại.")

    @staticmethod
    def create_criterion(db: Session, payload: CriterionCreate) -> CriterionRead:
        EvaluationService._ensure_unique_name(db, payload.name)
        now = _now()
        criterion = EvaluationCriterion(
            name=payload.name,
            description=payload.description,
            max_score=payload.max_score,
            weight=payload.weight,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        db.add(criterion)
        db.commit()
        db.refresh(criterion)
        return EvaluationService._criterion_read(criterion)

    @staticmethod
    def _get_criterion(db: Session, criterion_id: uuid.UUID) -> EvaluationCriterion:
        criterion = db.get(EvaluationCriterion, criterion_id)
        if criterion is None:
            raise ApiError(404, "CRITERION_NOT_FOUND", "Không tìm thấy tiêu chí đánh giá.")
        return criterion

    @staticmethod
    def update_criterion(
        db: Session, criterion_id: uuid.UUID, payload: CriterionUpdate
    ) -> CriterionRead:
        criterion = EvaluationService._get_criterion(db, criterion_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("name") is not None:
            EvaluationService._ensure_unique_name(db, data["name"], exclude_id=criterion.id)
            criterion.name = data["name"]
        if "description" in data:
            criterion.description = data["description"]
        if data.get("max_score") is not None:
            criterion.max_score = data["max_score"]
        if data.get("weight") is not None:
            criterion.weight = data["weight"]
        if data.get("status") is not None:
            criterion.status = data["status"]
        criterion.updated_at = _now()
        db.commit()
        db.refresh(criterion)
        return EvaluationService._criterion_read(criterion)

    @staticmethod
    def delete_criterion(db: Session, criterion_id: uuid.UUID) -> None:
        criterion = EvaluationService._get_criterion(db, criterion_id)
        in_use = db.scalar(
            select(Evaluation.id)
            .where(Evaluation.criteria_scores.contains([{"criterion_id": str(criterion.id)}]))
            .limit(1)
        )
        if in_use is not None:
            raise ApiError(
                409,
                "CRITERION_IN_USE",
                "Tiêu chí đã được dùng trong đánh giá nên không thể xóa. "
                "Hãy chuyển sang ngừng áp dụng.",
            )
        db.delete(criterion)
        db.commit()

    # ------------------------------------------------------------------
    # Tính điểm
    # ------------------------------------------------------------------

    @staticmethod
    def _active_criteria(db: Session) -> list[EvaluationCriterion]:
        return list(
            db.scalars(
                select(EvaluationCriterion)
                .where(EvaluationCriterion.status == "ACTIVE")
                .order_by(EvaluationCriterion.created_at.asc(), EvaluationCriterion.name.asc())
            )
        )

    @staticmethod
    def _resolve_scores(
        db: Session, inputs: list[ScoreInput], *, require_complete: bool
    ) -> tuple[list[dict[str, Any]], float | None]:
        """Kiểm tra điểm, chụp lại thông tin tiêu chí và tính tổng điểm.

        Trả về (danh sách điểm đã chụp, tổng điểm hoặc None nếu chưa chấm đủ).
        """
        active = EvaluationService._active_criteria(db)
        by_id = {criterion.id: criterion for criterion in active}
        scored: dict[uuid.UUID, dict[str, Any]] = {}
        for item in inputs:
            criterion = by_id.get(item.criterion_id)
            if criterion is None:
                raise ApiError(
                    422,
                    "INVALID_CRITERION",
                    "Có tiêu chí không tồn tại hoặc đã ngừng áp dụng.",
                    {"criterion_id": str(item.criterion_id)},
                )
            if item.criterion_id in scored:
                raise ApiError(
                    422,
                    "DUPLICATE_CRITERION",
                    "Mỗi tiêu chí chỉ được chấm một lần.",
                    {"criterion_id": str(item.criterion_id)},
                )
            max_score = _f(criterion.max_score)
            if item.score > max_score:
                raise ApiError(
                    422,
                    "SCORE_OUT_OF_RANGE",
                    f"Điểm của tiêu chí '{criterion.name}' không được vượt quá {max_score:g}.",
                    {"criterion_id": str(criterion.id), "max_score": max_score},
                )
            scored[criterion.id] = {
                "criterion_id": str(criterion.id),
                "name": criterion.name,
                "max_score": max_score,
                "weight": _f(criterion.weight),
                "score": round(item.score, 2),
            }

        items = [scored[criterion.id] for criterion in active if criterion.id in scored]
        complete = bool(active) and len(items) == len(active)
        if require_complete:
            if not active:
                raise ApiError(
                    409, "NO_ACTIVE_CRITERIA", "Chưa có tiêu chí đánh giá nào đang áp dụng."
                )
            if not complete:
                missing = [c.name for c in active if c.id not in scored]
                raise ApiError(
                    409,
                    "INCOMPLETE_EVALUATION",
                    "Cần chấm đủ điểm cho mọi tiêu chí trước khi công bố.",
                    {"missing_criteria": missing},
                )
        return items, (compute_total(items) if complete else None)

    # ------------------------------------------------------------------
    # Phạm vi dữ liệu
    # ------------------------------------------------------------------

    @staticmethod
    def _mentor_member(db: Session, user: User, member_id: uuid.UUID) -> InternshipMember:
        member = db.scalar(
            select(InternshipMember).where(
                InternshipMember.id == member_id, InternshipMember.mentor_id == user.id
            )
        )
        if member is None:
            raise ApiError(404, "MEMBER_NOT_FOUND", "Không tìm thấy Intern do bạn phụ trách.")
        return member

    @staticmethod
    def _visible_query(user: User):
        """Truy vấn đánh giá mà người dùng được phép đọc."""
        query = select(Evaluation).join(
            InternshipMember, InternshipMember.id == Evaluation.internship_member_id
        )
        if user.role == UserRole.MENTOR:
            return query.where(InternshipMember.mentor_id == user.id)
        if user.role == UserRole.INTERN:
            return query.where(
                InternshipMember.intern_id == user.id, Evaluation.status == "PUBLISHED"
            )
        return query  # ADMIN: đọc tất cả để giám sát

    @staticmethod
    def _get_visible(db: Session, user: User, evaluation_id: uuid.UUID) -> Evaluation:
        evaluation = db.scalar(
            EvaluationService._visible_query(user).where(Evaluation.id == evaluation_id)
        )
        if evaluation is None:
            raise ApiError(404, "EVALUATION_NOT_FOUND", "Không tìm thấy đánh giá.")
        return evaluation

    @staticmethod
    def _get_mentor_draft(db: Session, user: User, evaluation_id: uuid.UUID) -> Evaluation:
        evaluation = EvaluationService._get_visible(db, user, evaluation_id)
        if evaluation.status != "DRAFT":
            raise ApiError(
                409,
                "EVALUATION_ALREADY_PUBLISHED",
                "Đánh giá đã công bố nên không thể chỉnh sửa.",
            )
        return evaluation

    # ------------------------------------------------------------------
    # Đọc
    # ------------------------------------------------------------------

    @staticmethod
    def list_evaluations(
        db: Session,
        user: User,
        member_id: uuid.UUID | None = None,
        status: str | None = None,
        evaluation_type: str | None = None,
    ) -> list[EvaluationRead]:
        query = EvaluationService._visible_query(user)
        if member_id is not None:
            query = query.where(Evaluation.internship_member_id == member_id)
        if status in ("DRAFT", "PUBLISHED"):
            query = query.where(Evaluation.status == status)
        if evaluation_type in ("WEEKLY", "PERIODIC", "FINAL"):
            query = query.where(Evaluation.evaluation_type == evaluation_type)
        rows = list(db.scalars(query.order_by(Evaluation.updated_at.desc())))
        return EvaluationService._to_reads(db, rows)

    @staticmethod
    def get_evaluation(db: Session, user: User, evaluation_id: uuid.UUID) -> EvaluationRead:
        evaluation = EvaluationService._get_visible(db, user, evaluation_id)
        return EvaluationService._to_reads(db, [evaluation])[0]

    @staticmethod
    def _to_reads(db: Session, evaluations: list[Evaluation]) -> list[EvaluationRead]:
        if not evaluations:
            return []
        member_ids = {e.internship_member_id for e in evaluations}
        members = {
            m.id: m
            for m in db.scalars(select(InternshipMember).where(InternshipMember.id.in_(member_ids)))
        }
        user_ids = {m.intern_id for m in members.values()} | {e.mentor_id for e in evaluations}
        users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))}
        internship_ids = {m.internship_id for m in members.values()}
        internships = {
            i.id: i for i in db.scalars(select(Internship).where(Internship.id.in_(internship_ids)))
        }

        # Dữ liệu cũ (seed) chưa có bản chụp tiêu chí: tra tên/thang điểm hiện tại.
        legacy_ids: set[uuid.UUID] = set()
        for evaluation in evaluations:
            for entry in evaluation.criteria_scores or []:
                if isinstance(entry, dict) and "name" not in entry:
                    try:
                        legacy_ids.add(uuid.UUID(str(entry.get("criterion_id"))))
                    except ValueError:
                        continue
        criteria = (
            {
                c.id: c
                for c in db.scalars(
                    select(EvaluationCriterion).where(EvaluationCriterion.id.in_(legacy_ids))
                )
            }
            if legacy_ids
            else {}
        )

        reads: list[EvaluationRead] = []
        for evaluation in evaluations:
            member = members[evaluation.internship_member_id]
            intern = users.get(member.intern_id)
            mentor = users.get(evaluation.mentor_id)
            internship = internships.get(member.internship_id)
            reads.append(
                EvaluationRead(
                    id=evaluation.id,
                    internship_member_id=evaluation.internship_member_id,
                    intern_id=member.intern_id,
                    intern_name=intern.full_name if intern else "",
                    internship_name=internship.name if internship else None,
                    mentor_id=evaluation.mentor_id,
                    mentor_name=mentor.full_name if mentor else None,
                    evaluation_type=evaluation.evaluation_type,
                    scores=EvaluationService._score_reads(evaluation.criteria_scores, criteria),
                    total_score=(
                        _f(evaluation.total_score) if evaluation.total_score is not None else None
                    ),
                    comment=evaluation.comment,
                    week_start=evaluation.week_start,
                    week_end=evaluation.week_end,
                    verdict=evaluation.verdict,
                    verdict_reason=evaluation.verdict_reason,
                    status=evaluation.status,
                    published_at=evaluation.published_at,
                    created_at=evaluation.created_at,
                    updated_at=evaluation.updated_at,
                )
            )
        return reads

    @staticmethod
    def _score_reads(
        stored: list[Any] | None, criteria: dict[uuid.UUID, EvaluationCriterion]
    ) -> list[ScoreRead]:
        result: list[ScoreRead] = []
        for entry in stored or []:
            if not isinstance(entry, dict):
                continue
            try:
                criterion_id = uuid.UUID(str(entry.get("criterion_id")))
            except ValueError:
                continue
            if "name" in entry:
                name = str(entry["name"])
                max_score = _f(entry.get("max_score"))
                weight = _f(entry.get("weight"))
            else:
                criterion = criteria.get(criterion_id)
                name = criterion.name if criterion else "Tiêu chí đã bị xóa"
                max_score = _f(criterion.max_score) if criterion else 0.0
                weight = _f(criterion.weight) if criterion else 0.0
            result.append(
                ScoreRead(
                    criterion_id=criterion_id,
                    name=name,
                    max_score=max_score,
                    weight=weight,
                    score=_f(entry.get("score")),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Mentor lập, sửa nháp, công bố
    #
    # Ba loại đánh giá dùng chung một vòng đời (nháp, công bố):
    # - WEEKLY: nhận xét theo tuần (ngày bắt đầu, ngày kết thúc, nội dung), không chấm điểm.
    # - PERIODIC: đánh giá định kỳ, chấm điểm theo tiêu chí.
    # - FINAL: đánh giá cuối cùng, chấm điểm theo tiêu chí kèm kết luận Đạt/Chưa đạt và lý do.
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(text: str | None) -> str | None:
        return (text or "").strip() or None

    @staticmethod
    def _validate_type_fields(
        evaluation_type: str,
        week_start: date | None,
        week_end: date | None,
        has_verdict: bool,
        has_scores: bool,
    ) -> None:
        """Kiểm tra các trường đặc thù theo loại đánh giá."""
        if evaluation_type == "WEEKLY":
            if week_start is None or week_end is None:
                raise ApiError(
                    422,
                    "WEEK_RANGE_REQUIRED",
                    "Nhận xét tuần cần có ngày bắt đầu và ngày kết thúc.",
                )
            if week_end < week_start:
                raise ApiError(
                    422,
                    "WEEK_RANGE_INVALID",
                    "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.",
                )
            if (week_end - week_start).days + 1 > WEEKLY_MAX_DAYS:
                raise ApiError(
                    422,
                    "WEEK_RANGE_TOO_LONG",
                    f"Một nhận xét tuần không dài quá {WEEKLY_MAX_DAYS} ngày.",
                    {"max_days": WEEKLY_MAX_DAYS},
                )
            if has_scores:
                raise ApiError(
                    422, "WEEKLY_NO_SCORES", "Nhận xét tuần không chấm điểm theo tiêu chí."
                )
        elif week_start is not None or week_end is not None:
            raise ApiError(
                422,
                "WEEK_NOT_ALLOWED",
                "Chỉ nhận xét tuần mới có ngày bắt đầu và ngày kết thúc.",
            )
        if has_verdict and evaluation_type != "FINAL":
            raise ApiError(
                422,
                "VERDICT_NOT_ALLOWED",
                "Chỉ đánh giá cuối cùng mới có kết luận Đạt/Chưa đạt và lý do.",
            )

    @staticmethod
    def _ensure_no_week_overlap(
        db: Session,
        member_id: uuid.UUID,
        start: date,
        end: date,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(Evaluation).where(
            Evaluation.internship_member_id == member_id,
            Evaluation.evaluation_type == "WEEKLY",
            Evaluation.week_start <= end,
            Evaluation.week_end >= start,
        )
        if exclude_id is not None:
            query = query.where(Evaluation.id != exclude_id)
        clash = db.scalar(query.limit(1))
        if clash is not None and clash.week_start and clash.week_end:
            raise ApiError(
                409,
                "WEEK_OVERLAP",
                "Intern này đã có nhận xét tuần trùng khoảng thời gian đã chọn.",
                {
                    "week_start": clash.week_start.isoformat(),
                    "week_end": clash.week_end.isoformat(),
                },
            )

    @staticmethod
    def _ensure_single_final(
        db: Session, member_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(Evaluation.id).where(
            Evaluation.internship_member_id == member_id,
            Evaluation.evaluation_type == "FINAL",
        )
        if exclude_id is not None:
            query = query.where(Evaluation.id != exclude_id)
        if db.scalar(query.limit(1)) is not None:
            raise ApiError(409, "FINAL_EXISTS", "Intern này đã có đánh giá cuối cùng.")

    @staticmethod
    def _commit(db: Session) -> None:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ApiError(
                409,
                "EVALUATION_CONFLICT",
                "Không lưu được đánh giá do xung đột dữ liệu, vui lòng thử lại.",
            ) from None

    @staticmethod
    def create_evaluation(db: Session, user: User, payload: EvaluationCreate) -> EvaluationRead:
        member = EvaluationService._mentor_member(db, user, payload.internship_member_id)
        kind = payload.evaluation_type
        reason = EvaluationService._clean(payload.verdict_reason)
        EvaluationService._validate_type_fields(
            kind,
            payload.week_start,
            payload.week_end,
            has_verdict=payload.verdict is not None or reason is not None,
            has_scores=bool(payload.scores),
        )
        if kind == "WEEKLY":
            EvaluationService._ensure_no_week_overlap(
                db,
                member.id,
                payload.week_start,
                payload.week_end,  # type: ignore[arg-type]
            )
            items: list[dict[str, Any]] = []
            total: float | None = None
        else:
            if kind == "FINAL":
                EvaluationService._ensure_single_final(db, member.id)
            items, total = EvaluationService._resolve_scores(
                db, payload.scores, require_complete=False
            )
        now = _now()
        evaluation = Evaluation(
            internship_member_id=member.id,
            mentor_id=user.id,
            evaluation_type=kind,
            criteria_scores=items,
            total_score=total,
            comment=EvaluationService._clean(payload.comment),
            week_start=payload.week_start,
            week_end=payload.week_end,
            verdict=payload.verdict,
            verdict_reason=reason,
            status="DRAFT",
            created_at=now,
            updated_at=now,
        )
        db.add(evaluation)
        EvaluationService._commit(db)
        db.refresh(evaluation)
        return EvaluationService._to_reads(db, [evaluation])[0]

    @staticmethod
    def update_evaluation(
        db: Session, user: User, evaluation_id: uuid.UUID, payload: EvaluationUpdate
    ) -> EvaluationRead:
        evaluation = EvaluationService._get_mentor_draft(db, user, evaluation_id)
        data = payload.model_dump(exclude_unset=True)
        kind = evaluation.evaluation_type
        if data.get("evaluation_type") not in (None, kind):
            raise ApiError(
                422,
                "TYPE_IMMUTABLE",
                "Không đổi được loại đánh giá của bản nháp. Hãy tạo đánh giá mới.",
            )
        week_start = data["week_start"] if "week_start" in data else evaluation.week_start
        week_end = data["week_end"] if "week_end" in data else evaluation.week_end
        verdict = data["verdict"] if "verdict" in data else evaluation.verdict
        reason = (
            EvaluationService._clean(data["verdict_reason"])
            if "verdict_reason" in data
            else evaluation.verdict_reason
        )
        EvaluationService._validate_type_fields(
            kind,
            week_start,
            week_end,
            has_verdict=verdict is not None or reason is not None,
            has_scores=bool(payload.scores),
        )
        if kind == "WEEKLY":
            EvaluationService._ensure_no_week_overlap(
                db,
                evaluation.internship_member_id,
                week_start,
                week_end,
                evaluation.id,  # type: ignore[arg-type]
            )
        evaluation.week_start = week_start
        evaluation.week_end = week_end
        evaluation.verdict = verdict
        evaluation.verdict_reason = reason
        if "comment" in data:
            evaluation.comment = EvaluationService._clean(data["comment"])
        if payload.scores is not None and kind != "WEEKLY":
            items, total = EvaluationService._resolve_scores(
                db, payload.scores, require_complete=False
            )
            evaluation.criteria_scores = items
            evaluation.total_score = total
        evaluation.updated_at = _now()
        EvaluationService._commit(db)
        db.refresh(evaluation)
        return EvaluationService._to_reads(db, [evaluation])[0]

    @staticmethod
    def publish_evaluation(db: Session, user: User, evaluation_id: uuid.UUID) -> EvaluationRead:
        evaluation = EvaluationService._get_mentor_draft(db, user, evaluation_id)
        kind = evaluation.evaluation_type
        items: list[dict[str, Any]]
        total: float | None
        if kind == "WEEKLY":
            if EvaluationService._clean(evaluation.comment) is None:
                raise ApiError(
                    409,
                    "WEEKLY_CONTENT_REQUIRED",
                    "Cần nhập nội dung nhận xét tuần trước khi công bố.",
                )
            items, total = [], None
        else:
            if kind == "FINAL" and (
                evaluation.verdict is None
                or EvaluationService._clean(evaluation.verdict_reason) is None
            ):
                raise ApiError(
                    409,
                    "FINAL_VERDICT_REQUIRED",
                    "Đánh giá cuối cùng cần có kết luận Đạt/Chưa đạt và lý do trước khi công bố.",
                )
            stored: list[ScoreInput] = []
            for entry in evaluation.criteria_scores or []:
                if not isinstance(entry, dict):
                    continue
                try:
                    stored.append(
                        ScoreInput(
                            criterion_id=uuid.UUID(str(entry.get("criterion_id"))),
                            score=_f(entry.get("score")),
                        )
                    )
                except (ValueError, TypeError):
                    continue
            # Chấm lại theo tiêu chí đang áp dụng lúc công bố; tiêu chí đã ngừng bị bỏ qua.
            active_ids = {criterion.id for criterion in EvaluationService._active_criteria(db)}
            retained = [item for item in stored if item.criterion_id in active_ids]
            items, total = EvaluationService._resolve_scores(db, retained, require_complete=True)
        now = _now()
        evaluation.criteria_scores = items
        evaluation.total_score = total
        evaluation.status = "PUBLISHED"
        evaluation.published_at = now
        evaluation.updated_at = now
        EvaluationService._commit(db)
        db.refresh(evaluation)
        return EvaluationService._to_reads(db, [evaluation])[0]
