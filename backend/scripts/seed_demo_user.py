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

DEMO_EMAIL = "intern@itms.local"
DEMO_PASSWORD = "Intern@12345"


def main() -> None:
    session_factory = get_session_factory()
    with session_factory.begin() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            db.add(
                User(
                    email=DEMO_EMAIL,
                    password_hash=hash_password(DEMO_PASSWORD),
                    full_name="Thực tập sinh Demo",
                    role=UserRole.INTERN,
                    status=UserStatus.ACTIVE,
                )
            )
            print(f"Created development user: {DEMO_EMAIL}")
            return

        user.password_hash = hash_password(DEMO_PASSWORD)
        user.status = UserStatus.ACTIVE
        print(f"Reset development user password: {DEMO_EMAIL}")


if __name__ == "__main__":
    main()
