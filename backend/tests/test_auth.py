import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, OpenerDirector, Request, build_opener, urlopen
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.core import security
from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.core.settings import get_settings
from app.models.auth import AuthSession
from app.models.enums import UserRole, UserStatus
from app.models.user import User

PROJECT_ROOT = Path(__file__).parents[1]
DEMO_USER_ID = "a0b59b90-3c25-4b08-92d5-e04269c9da31"
DEMO_USER_UUID = UUID(DEMO_USER_ID)


@pytest.fixture(autouse=True)
def auth_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Give the Uvicorn process a persisted database containing a real user."""
    database_path = tmp_path / "auth.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    User.__table__.create(engine)
    AuthSession.__table__.create(engine)
    with Session(engine) as db:
        db.add(
            User(
                id=DEMO_USER_UUID,
                email="intern@itms.local",
                password_hash=hash_password("Intern@12345"),
                full_name="Thực tập sinh Demo",
                role=UserRole.INTERN,
                status=UserStatus.ACTIVE,
            )
        )
        db.commit()
    engine.dispose()
    monkeypatch.setenv("ITMS_DATABASE_URL", database_url)
    monkeypatch.setenv("ITMS_JWT_SECRET", "test-secret-only")
    # The server subprocess inherits this environment. Disable real SMTP so
    # endpoint tests remain deterministic and never send external email.
    monkeypatch.setenv("ITMS_SMTP_USERNAME", "")
    monkeypatch.setenv("ITMS_SMTP_PASSWORD", "")
    monkeypatch.setenv("ITMS_SMTP_FROM_EMAIL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def active_user(db: Session) -> User:
    user = db.get(User, DEMO_USER_UUID)
    assert user is not None
    return user


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@contextmanager
def _running_server():  # type: ignore[no-untyped-def]
    port = _available_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.terminate()
        with suppress(subprocess.TimeoutExpired):
            server.wait(timeout=3)
        if server.poll() is None:
            server.kill()


def _request_json(
    method: str,
    url: str,
    payload: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(url, data=body, headers=request_headers, method=method)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urlopen(request, timeout=2.0) as response:  # noqa: S310
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not expose the authentication endpoint within five seconds.")


def _request_with_headers(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    opener: OpenerDirector | None = None,
) -> tuple[int, dict[str, Any], Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(url, data=body, headers=request_headers, method=method)
    open_request = opener.open if opener is not None else urlopen
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with open_request(request, timeout=2.0) as response:
                return response.status, json.loads(response.read()), response.headers
        except HTTPError as error:
            return error.code, json.loads(error.read()), error.headers
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not expose the endpoint within five seconds.")


def test_login_sets_httponly_cookie_and_refresh_rotates_it() -> None:
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    with _running_server() as base_url:
        login_status, login_body, login_headers = _request_with_headers(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {
                "email": "intern@itms.local",
                "password": "Intern@12345",
                "remember_me": False,
            },
            opener=opener,
        )
        set_cookie = login_headers.get("Set-Cookie", "")

        refresh_status, refresh_body, refresh_headers = _request_with_headers(
            "POST", f"{base_url}/api/v1/auth/refresh", opener=opener
        )

    assert login_status == 200
    assert "HttpOnly" in set_cookie
    assert "Max-Age" not in set_cookie
    assert refresh_status == 200
    assert refresh_body["access_token"] != login_body["access_token"]
    assert "HttpOnly" in refresh_headers.get("Set-Cookie", "")


def test_production_rejects_x_user_id_and_bearer_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ITMS_ENVIRONMENT", "production")
    get_settings.cache_clear()
    with _running_server() as base_url:
        header_status, _, _ = _request_with_headers(
            "GET",
            f"{base_url}/api/v1/users",
            headers={"X-User-Id": DEMO_USER_ID},
        )
        bearer_status, _, _ = _request_with_headers(
            "GET",
            f"{base_url}/api/v1/users",
            headers={"Authorization": f"Bearer {DEMO_USER_ID}"},
        )

    assert header_status == 401
    assert bearer_status == 401


def test_login_issues_access_token_and_allows_me_request() -> None:
    with _running_server() as base_url:
        login_status, login_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "INTERN@ITMS.LOCAL", "password": "Intern@12345"},
        )

        assert login_status == 200
        assert login_body["token_type"] == "bearer"
        assert login_body["expires_in"] == 900
        assert login_body["user"] == {
            "id": DEMO_USER_ID,
            "email": "intern@itms.local",
            "full_name": "Thực tập sinh Demo",
            "role": "INTERN",
            "avatar_url": None,
        }

        me_status, me_body = _request_json(
            "GET",
            f"{base_url}/api/v1/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )

    assert me_status == 200
    assert me_body == login_body["user"]


def test_refresh_token_contains_session_id_and_only_hash_is_stable() -> None:
    session_id = uuid4()

    token = security.create_refresh_token(session_id)

    assert token.startswith(f"{session_id}.")
    assert security.hash_refresh_token(token) == security.hash_refresh_token(token)
    assert token != security.hash_refresh_token(token)


def test_refresh_settings_have_secure_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "ITMS_SESSION_REFRESH_TTL_SECONDS",
        "ITMS_REMEMBERED_REFRESH_TTL_SECONDS",
        "ITMS_REFRESH_COOKIE_NAME",
    ):
        monkeypatch.delenv(variable, raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.session_refresh_ttl_seconds == 43_200
    assert settings.remembered_refresh_ttl_seconds == 2_592_000
    assert settings.refresh_cookie_name == "itms_refresh_token"


def test_persisted_session_survives_service_recreation(db: Session, active_user: User) -> None:
    settings = get_settings()

    login = AuthService().login(db, active_user.email, "Intern@12345", settings, remember_me=False)
    account = AuthService().get_account_from_access_token(db, login.access_token, settings)

    assert account.id == active_user.id


def test_refresh_rotates_token_and_rejects_reuse(db: Session, active_user: User) -> None:
    settings = get_settings()
    service = AuthService()
    login = service.login(db, active_user.email, "Intern@12345", settings, remember_me=True)

    refreshed = AuthService().refresh(db, login.refresh_token, settings)

    assert refreshed.refresh_token != login.refresh_token
    with pytest.raises(ApiError) as error:
        AuthService().refresh(db, login.refresh_token, settings)
    assert error.value.code == "INVALID_REFRESH_TOKEN"


def test_logout_revokes_only_current_session(db: Session, active_user: User) -> None:
    settings = get_settings()
    service = AuthService()
    first = service.login(db, active_user.email, "Intern@12345", settings, remember_me=False)
    second = service.login(db, active_user.email, "Intern@12345", settings, remember_me=False)

    service.logout(db, first.refresh_token, settings)

    with pytest.raises(ApiError):
        service.get_account_from_access_token(db, first.access_token, settings)
    assert (
        service.get_account_from_access_token(db, second.access_token, settings).id
        == active_user.id
    )


def test_password_change_revokes_every_session(db: Session, active_user: User) -> None:
    settings = get_settings()
    service = AuthService()
    first = service.login(db, active_user.email, "Intern@12345", settings, remember_me=False)
    second = service.login(db, active_user.email, "Intern@12345", settings, remember_me=True)
    account = service.get_account_from_access_token(db, first.access_token, settings)

    service.change_password(db, account, "Intern@12345", "Changed@12345")

    for token in (first.access_token, second.access_token):
        with pytest.raises(ApiError):
            service.get_account_from_access_token(db, token, settings)


def test_login_rejects_invalid_credentials_without_disclosing_account() -> None:
    with _running_server() as base_url:
        status, body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "intern@itms.local", "password": "wrong-password"},
        )

    assert status == 401
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Email hoặc mật khẩu không chính xác."


def test_password_lifecycle_refresh_and_logout() -> None:
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    with _running_server() as base_url:
        login_status, login_body, _ = _request_with_headers(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "intern@itms.local", "password": "Intern@12345"},
            opener=opener,
        )
        assert login_status == 200

        refresh_status, refresh_body, _ = _request_with_headers(
            "POST", f"{base_url}/api/v1/auth/refresh", opener=opener
        )
        assert refresh_status == 200
        assert refresh_body["user"]["email"] == "intern@itms.local"
        authorization = {"Authorization": f"Bearer {refresh_body['access_token']}"}

        change_status, change_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/change-password",
            {"current_password": "Intern@12345", "new_password": "Changed@12345"},
            authorization,
        )
        assert change_status == 200
        assert change_body["message"] == "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."

        revoked_status, revoked_body = _request_json(
            "GET", f"{base_url}/api/v1/me", headers=authorization
        )
        assert revoked_status == 401
        assert revoked_body["error"]["code"] == "INVALID_ACCESS_TOKEN"

        relogin_status, relogin_body, _ = _request_with_headers(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "intern@itms.local", "password": "Changed@12345"},
            opener=opener,
        )
        assert relogin_status == 200
        fresh_authorization = {"Authorization": f"Bearer {relogin_body['access_token']}"}

        logout_status, logout_body, _ = _request_with_headers(
            "POST", f"{base_url}/api/v1/auth/logout", opener=opener
        )
        assert logout_status == 200
        assert logout_body == {"message": "Đã đăng xuất."}

        after_logout_status, after_logout_body = _request_json(
            "GET", f"{base_url}/api/v1/me", headers=fresh_authorization
        )
        assert after_logout_status == 401
        assert after_logout_body["error"]["code"] == "INVALID_ACCESS_TOKEN"


def test_forgot_and_reset_password_do_not_disclose_unknown_email() -> None:
    with _running_server() as base_url:
        unknown_status, unknown_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/forgot-password",
            {"email": "unknown@itms.local"},
        )
        reset_request_status, reset_request_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/forgot-password",
            {"email": "intern@itms.local"},
        )
        assert unknown_status == reset_request_status == 200
        assert unknown_body["message"] == reset_request_body["message"]
        assert "otp" not in reset_request_body


def test_password_reset_otp_is_one_time_and_hashed(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'otp.db'}"
    engine = create_engine(database_url)
    User.__table__.create(engine)
    AuthSession.__table__.create(engine)
    service = AuthService()
    with Session(engine) as db:
        user = User(
            id=DEMO_USER_UUID,
            email="intern@itms.local",
            password_hash=hash_password("Intern@12345"),
            full_name="Thực tập sinh Demo",
            role=UserRole.INTERN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        result = service.create_password_reset_otp(db, user.email, get_settings())
        assert result is not None
        _, otp = result
        assert otp.isdigit() and len(otp) == 6
        assert user.password_reset_token_hash != otp

        with pytest.raises(ApiError, match="Mã OTP"):
            service.reset_password(db, "other@itms.local", otp, "Reset@12345", get_settings())
        service.reset_password(db, user.email, otp, "Reset@12345", get_settings())
        assert user.password_reset_token_hash is None
        assert verify_password("Reset@12345", user.password_hash)
        with pytest.raises(ApiError, match="Mã OTP"):
            service.reset_password(db, user.email, otp, "Another@12345", get_settings())
    engine.dispose()
