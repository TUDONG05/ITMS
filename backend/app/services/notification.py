from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.interaction import Notification, NotificationRead
from app.models.user import User
from app.schemas.notification import NotificationCreate


class NotificationService:
    @staticmethod
    def _can_receive(notification: Notification, user: User) -> bool:
        """Kiểm tra user có được nhận notification này không."""
        t = notification.target_type
        if t == "ALL":
            return True
        if t == "ROLE":
            roles: list[str] = notification.target_data or []
            return str(user.role) in roles
        if t == "USER":
            user_ids: list[str] = notification.target_data or []
            return str(user.id) in user_ids
        return False

    @classmethod
    def create_notification(cls, db: Session, actor: User, data: NotificationCreate) -> dict:
        """Admin tạo + gửi thông báo."""
        if str(actor.role) != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can create notifications"
            )
        notif = Notification(
            title=data.title.strip(),
            content=data.content.strip(),
            target_type=data.target_type,
            target_data=data.target_data,
            created_by=actor.id,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return cls._to_dict(notif, actor.full_name, is_read=False, read_count=0)

    @classmethod
    def list_notifications_admin(cls, db: Session, actor: User) -> list[dict]:
        """Admin xem danh sách thông báo đã gửi (tất cả)."""
        if str(actor.role) != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin can view all notifications",
            )
        notifications = db.query(Notification).order_by(Notification.created_at.desc()).all()
        result = []
        for n in notifications:
            creator = db.query(User).filter(User.id == n.created_by).first()
            read_count = (
                db.query(NotificationRead).filter(NotificationRead.notification_id == n.id).count()
            )
            result.append(
                cls._to_dict(
                    n, creator.full_name if creator else None, is_read=False, read_count=read_count
                )
            )
        return result

    @classmethod
    def list_notifications_user(cls, db: Session, user: User) -> list[dict]:
        """Intern/Mentor xem danh sách thông báo của mình."""
        all_notifs = db.query(Notification).order_by(Notification.created_at.desc()).all()
        result = []
        for n in all_notifs:
            if not cls._can_receive(n, user):
                continue
            creator = db.query(User).filter(User.id == n.created_by).first()
            read_rec = (
                db.query(NotificationRead)
                .filter(
                    NotificationRead.notification_id == n.id,
                    NotificationRead.user_id == user.id,
                )
                .first()
            )
            result.append(
                cls._to_dict(
                    n,
                    creator.full_name if creator else None,
                    is_read=read_rec is not None,
                    read_count=0,
                    read_at=read_rec.read_at if read_rec else None,
                )
            )
        return result

    @classmethod
    def get_notification_detail(cls, db: Session, user: User, notif_id: uuid.UUID) -> dict:
        """Xem chi tiết một thông báo."""
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        # Admin có thể xem tất cả; Intern/Mentor chỉ xem thông báo dành cho mình
        if str(user.role) != UserRole.ADMIN and not cls._can_receive(notif, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this notification",
            )
        creator = db.query(User).filter(User.id == notif.created_by).first()
        read_rec = None
        if str(user.role) != UserRole.ADMIN:
            read_rec = (
                db.query(NotificationRead)
                .filter(
                    NotificationRead.notification_id == notif.id,
                    NotificationRead.user_id == user.id,
                )
                .first()
            )
        read_count = (
            db.query(NotificationRead).filter(NotificationRead.notification_id == notif.id).count()
        )
        return cls._to_dict(
            notif,
            creator.full_name if creator else None,
            is_read=read_rec is not None,
            read_count=read_count,
            read_at=read_rec.read_at if read_rec else None,
        )

    @classmethod
    def mark_as_read(cls, db: Session, user: User, notif_id: uuid.UUID) -> dict:
        """Intern/Mentor đánh dấu đã đọc."""
        if str(user.role) == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin does not need to mark notifications as read",
            )
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        if not cls._can_receive(notif, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this notification"
            )
        existing = (
            db.query(NotificationRead)
            .filter(
                NotificationRead.notification_id == notif_id,
                NotificationRead.user_id == user.id,
            )
            .first()
        )
        if existing:
            # Already read — idempotent
            creator = db.query(User).filter(User.id == notif.created_by).first()
            return cls._to_dict(
                notif,
                creator.full_name if creator else None,
                is_read=True,
                read_count=0,
                read_at=existing.read_at,
            )
        read_rec = NotificationRead(notification_id=notif_id, user_id=user.id)
        db.add(read_rec)
        db.commit()
        db.refresh(read_rec)
        creator = db.query(User).filter(User.id == notif.created_by).first()
        return cls._to_dict(
            notif,
            creator.full_name if creator else None,
            is_read=True,
            read_count=0,
            read_at=read_rec.read_at,
        )

    @classmethod
    def mark_all_as_read(cls, db: Session, user: User) -> dict:
        """Đánh dấu tất cả thông báo của user là đã đọc."""
        if str(user.role) == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin does not need to mark notifications as read",
            )
        all_notifs = db.query(Notification).all()
        count = 0
        for n in all_notifs:
            if not cls._can_receive(n, user):
                continue
            existing = (
                db.query(NotificationRead)
                .filter(
                    NotificationRead.notification_id == n.id,
                    NotificationRead.user_id == user.id,
                )
                .first()
            )
            if not existing:
                db.add(NotificationRead(notification_id=n.id, user_id=user.id))
                count += 1
        db.commit()
        return {"marked_count": count}

    @classmethod
    def get_unread_count(cls, db: Session, user: User) -> int:
        """
        - Đối với Admin: Trả về tổng số thông báo trong hệ thống (đã gửi).
        - Đối với Intern/Mentor: Trả về số thông báo chưa đọc dành cho người dùng.
        """
        if str(user.role) == UserRole.ADMIN:
            return db.query(Notification).count()

        all_notifs = db.query(Notification).all()
        count = 0
        for n in all_notifs:
            if not cls._can_receive(n, user):
                continue
            existing = (
                db.query(NotificationRead)
                .filter(
                    NotificationRead.notification_id == n.id,
                    NotificationRead.user_id == user.id,
                )
                .first()
            )
            if not existing:
                count += 1
        return count

    @classmethod
    def delete_notification(cls, db: Session, actor: User, notif_id: uuid.UUID) -> None:
        """Admin xóa thông báo."""
        if str(actor.role) != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can delete notifications"
            )
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        db.delete(notif)
        db.commit()

    @staticmethod
    def _to_dict(
        n: Notification,
        creator_name: str | None,
        is_read: bool,
        read_count: int,
        read_at: datetime | None = None,
    ) -> dict:
        return {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "target_type": n.target_type,
            "target_data": n.target_data,
            "created_by": n.created_by,
            "created_at": n.created_at,
            "creator_name": creator_name,
            "is_read": is_read,
            "read_count": read_count,
            "read_at": read_at,
        }
