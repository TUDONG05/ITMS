"""Create the development account used to exercise the login flow.

Run this only after ``alembic upgrade head`` against a local development database.
"""

import sys
from pathlib import Path

from sqlalchemy import select

# Direct execution makes ``backend/scripts`` the import root. Include ``backend`` so the
# application's absolute imports work with the documented command.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.enums import UserRole, UserStatus
from app.models.user import User

DEMO_USERS = (
    ("intern@itms.local", "Intern@12345", "Nguyễn Văn An", UserRole.INTERN),
    ("intern2@itms.local", "Intern2@12345", "Trần Thị Bình", UserRole.INTERN),
    ("intern3@itms.local", "Intern3@12345", "Lê Minh Cường", UserRole.INTERN),
    ("mentor@itms.local", "Mentor@12345", "Lê Minh Hoàng", UserRole.MENTOR),
    ("mentor2@itms.local", "Mentor2@12345", "Trần Minh Bình", UserRole.MENTOR),
    ("admin@itms.local", "Admin@12345", "Quản trị viên ITMS", UserRole.ADMIN),
)


def main() -> None:
    session_factory = get_session_factory()
    with session_factory.begin() as db:
        for email, password, full_name, role in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(password),
                        full_name=full_name,
                        role=role,
                        status=UserStatus.ACTIVE,
                    )
                )
                print(f"Created development user: {email}")
            else:
                user.password_hash = hash_password(password)
                user.status = UserStatus.ACTIVE
                user.role = role
                print(f"Reset development user: {email}")


if __name__ == "__main__":
    main()
