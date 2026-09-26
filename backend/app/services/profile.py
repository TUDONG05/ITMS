"""UC-5 – Quản lý hồ sơ cá nhân.

Business rules
--------------
* Intern / Mentor / Admin đều có thể xem và cập nhật các trường được phép
  (phone, avatar_url) của *chính mình*.
* Admin thêm có thể cập nhật full_name của chính mình.
* Email KHÔNG được phép tự thay đổi qua endpoint này.
* Intern thêm xem được thông tin Mentor đang phụ trách (qua InternshipMember).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.internship import InternshipMember
from app.models.user import User

# ---------------------------------------------------------------------------
# Value objects returned by service functions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MentorSummary:
    id: UUID
    full_name: str
    email: str


@dataclass(frozen=True)
class ProfileRead:
    id: UUID
    email: str
    full_name: str
    phone: str | None
    avatar_url: str | None
    role: str
    status: str
    created_at: object  # datetime
    mentor: MentorSummary | None


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def get_profile(db: Session, user_id: UUID) -> ProfileRead:
    """Return the full profile for *user_id*, including Mentor info for interns."""
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng.")

    mentor: MentorSummary | None = None
    if user.role == "INTERN":
        mentor = _find_mentor(db, user_id)

    return _to_profile_read(user, mentor)


def update_profile(
    db: Session,
    user_id: UUID,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
) -> ProfileRead:
    """Cập nhật các trường được phép cho *user_id*.

    Admin có thể cập nhật full_name, phone, avatar_url.
    Các role khác (INTERN, MENTOR) chỉ có thể cập nhật phone, avatar_url.
    Email và role KHÔNG được thay đổi tại đây.
    """
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng.")

    # Chặn cập nhật nếu tài khoản bị khóa / không hoạt động
    if user.status != "ACTIVE":
        raise ApiError(
            403, "ACCOUNT_NOT_ACTIVE", "Tài khoản không có quyền thực hiện thao tác này."
        )

    changed = False

    if full_name is not None:
        if user.role != "ADMIN":
            raise ApiError(
                403, "FORBIDDEN", "Chỉ quản trị viên mới có quyền thay đổi họ và tên."
            )
        stripped = full_name.strip()
        if not stripped:
            raise ApiError(422, "INVALID_FULL_NAME", "Họ và tên không được để trống.")
        user.full_name = stripped
        changed = True

    if phone is not None:
        user.phone = phone.strip() or None
        changed = True
    if avatar_url is not None:
        user.avatar_url = avatar_url.strip() or None
        changed = True

    if changed:
        db.commit()
        db.refresh(user)

    mentor: MentorSummary | None = None
    if user.role == "INTERN":
        mentor = _find_mentor(db, user_id)

    return _to_profile_read(user, mentor)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _find_mentor(db: Session, intern_id: UUID) -> MentorSummary | None:
    """Tìm Mentor đang phụ trách intern trong đợt thực tập ACTIVE."""
    stmt = (
        select(InternshipMember)
        .where(
            InternshipMember.intern_id == intern_id,
            InternshipMember.mentor_id.isnot(None),
            InternshipMember.status.in_(["ACTIVE", "EXTENDED"]),
        )
        .order_by(InternshipMember.created_at.desc())
        .limit(1)
    )
    member = db.scalar(stmt)
    if member is None or member.mentor_id is None:
        return None

    mentor_user = db.get(User, member.mentor_id)
    if mentor_user is None:
        return None
    return MentorSummary(
        id=mentor_user.id,
        full_name=mentor_user.full_name,
        email=mentor_user.email,
    )


def _to_profile_read(user: User, mentor: MentorSummary | None) -> ProfileRead:
    return ProfileRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        mentor=mentor,
    )
