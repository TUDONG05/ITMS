from sqlalchemy import delete, select

from app.db.session import get_session_factory
from app.models.enums import UserRole, UserStatus
from app.models.user import User

LEAK_PROBE_EMAIL = "pytest-isolation-probe@invalid.local"


def test_01_committed_test_data_is_visible_inside_the_current_test() -> None:
    factory = get_session_factory()
    with factory() as session:
        session.execute(delete(User).where(User.email == LEAK_PROBE_EMAIL))
        session.commit()

        session.add(
            User(
                email=LEAK_PROBE_EMAIL,
                password_hash="not-a-real-password",
                full_name="Pytest isolation probe",
                role=UserRole.INTERN,
                status=UserStatus.ACTIVE,
            )
        )
        session.commit()

        assert session.scalar(select(User.id).where(User.email == LEAK_PROBE_EMAIL)) is not None


def test_02_committed_test_data_does_not_leak_into_the_next_test() -> None:
    factory = get_session_factory()
    with factory() as session:
        leaked_user = session.scalar(select(User).where(User.email == LEAK_PROBE_EMAIL))
        try:
            assert leaked_user is None
        finally:
            if leaked_user is not None:
                session.delete(leaked_user)
                session.commit()
