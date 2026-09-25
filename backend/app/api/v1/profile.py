"""UC-5 – API endpoints: GET /profile, PATCH /profile, POST /profile/avatar."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_account
from app.auth.service import Account
from app.core.errors import ApiError
from app.core.settings import AVATAR_UPLOAD_DIR
from app.db.session import get_db
from app.schemas.profile import InternProfileRead, MentorSummarySchema, UpdateProfileRequest
from app.services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])

_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_avatar_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("/uploads/"):
        return f"/api/v1{url}"
    return url


def _serialize_mentor(mentor: profile_service.MentorSummary | None) -> MentorSummarySchema | None:
    if mentor is None:
        return None
    return MentorSummarySchema(id=mentor.id, full_name=mentor.full_name, email=mentor.email)


def _serialize_profile(data: profile_service.ProfileRead) -> InternProfileRead:
    return InternProfileRead(
        id=data.id,
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        avatar_url=_normalize_avatar_url(data.avatar_url),
        role=data.role,
        status=data.status,
        created_at=data.created_at,
        mentor=_serialize_mentor(data.mentor),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=InternProfileRead, summary="Xem hồ sơ cá nhân")
def get_profile(
    account: Annotated[Account, Depends(get_current_account)],
    db: Annotated[Session, Depends(get_db)],
) -> InternProfileRead:
    """Trả về hồ sơ của người dùng hiện tại.

    * Với Intern: bao gồm thông tin Mentor đang phụ trách (nếu có).
    * Với Mentor / Admin: trường ``mentor`` luôn là ``null``.
    """
    data = profile_service.get_profile(db, account.id)
    return _serialize_profile(data)


@router.patch("", response_model=InternProfileRead, summary="Cập nhật hồ sơ cá nhân")
def update_profile(
    payload: UpdateProfileRequest,
    account: Annotated[Account, Depends(get_current_account)],
    db: Annotated[Session, Depends(get_db)],
) -> InternProfileRead:
    """Cập nhật các trường được phép: ``phone``, ``avatar_url``.

    Họ tên, email và role **không được phép** thay đổi qua endpoint này.
    Chỉ cập nhật trường có giá trị khác ``null``.
    """
    data = profile_service.update_profile(
        db,
        account.id,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
    )
    return _serialize_profile(data)


@router.post("/avatar", response_model=InternProfileRead, summary="Upload ảnh đại diện")
async def upload_avatar(
    file: UploadFile,
    account: Annotated[Account, Depends(get_current_account)],
    db: Annotated[Session, Depends(get_db)],
) -> InternProfileRead:
    """Nhận file ảnh (multipart/form-data, field name ``file``).

    * Định dạng cho phép: JPEG, PNG, WebP, GIF.
    * Kích thước tối đa: 2 MB.
    * Lưu vào ``uploads/avatars/<uuid>.<ext>`` và cập nhật ``avatar_url`` của người dùng.
    """
    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_MIME:
        raise ApiError(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "Chỉ chấp nhận ảnh JPEG, PNG, WebP hoặc GIF.",
        )

    # Đọc nội dung và kiểm tra kích thước
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise ApiError(413, "FILE_TOO_LARGE", "Kích thước ảnh không được vượt quá 2 MB.")

    # Xác định extension từ MIME
    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = ext_map[content_type]

    # Lưu file với tên ngẫu nhiên
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = AVATAR_UPLOAD_DIR / filename
    dest.write_bytes(content)

    # Cập nhật avatar_url trong DB
    avatar_url = f"/uploads/avatars/{filename}"
    data = profile_service.update_profile(
        db,
        account.id,
        phone=None,
        avatar_url=avatar_url,
    )
    return _serialize_profile(data)
