import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationListItem,
    NotificationRead,
    NotificationUpdate,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

ADMIN_ONLY = [UserRole.ADMIN]
ALL_ROLES = [UserRole.ADMIN, UserRole.MENTOR, UserRole.INTERN]
USER_ROLES = [UserRole.MENTOR, UserRole.INTERN]


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    current_user: User = Depends(require_roles(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    """Admin tạo và gửi thông báo."""
    return NotificationService.create_notification(db, current_user, payload)


@router.get("", response_model=list[NotificationListItem])
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin: xem tất cả thông báo đã gửi. Intern/Mentor: xem thông báo dành cho mình."""
    if str(current_user.role) == UserRole.ADMIN:
        return NotificationService.list_notifications_admin(db, current_user)
    return NotificationService.list_notifications_user(db, current_user)


@router.post("/read-all", response_model=dict)
def mark_all_as_read(
    current_user: User = Depends(require_roles(USER_ROLES)),
    db: Session = Depends(get_db),
):
    """Intern/Mentor đánh dấu tất cả thông báo đã đọc."""
    return NotificationService.mark_all_as_read(db, current_user)


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy số thông báo chưa đọc của người dùng hiện tại."""
    count = NotificationService.get_unread_count(db, current_user)
    return {"unread_count": count}


@router.get("/{notification_id}", response_model=NotificationRead)
def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xem chi tiết một thông báo."""
    return NotificationService.get_notification_detail(db, current_user, notification_id)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_roles(USER_ROLES)),
    db: Session = Depends(get_db),
):
    """Intern/Mentor đánh dấu thông báo đã đọc."""
    return NotificationService.mark_as_read(db, current_user, notification_id)


@router.put("/{notification_id}", response_model=NotificationRead)
def update_notification(
    notification_id: uuid.UUID,
    payload: NotificationUpdate,
    current_user: User = Depends(require_roles(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    """Admin chỉnh sửa thông báo (tiêu đề, nội dung, đối tượng nhận)."""
    return NotificationService.update_notification(db, current_user, notification_id, payload)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_roles(ADMIN_ONLY)),
    db: Session = Depends(get_db),
) -> Response:
    """Admin xóa thông báo."""
    NotificationService.delete_notification(db, current_user, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
