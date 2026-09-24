import json
import socket
import subprocess
import sys
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.core.settings import get_settings
from app.models.enums import UserRole, UserStatus
from app.models.user import User

PROJECT_ROOT = Path(__file__).parents[1]
DEMO_USER_ID = "a0b59b90-3c25-4b08-92d5-e04269c9da31"
DEMO_USER_UUID = UUID(DEMO_USER_ID)


@pytest.fixture(autouse=True)
def auth_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the Uvicorn process a persisted database containing a real user."""
    database_path = tmp_path / "auth.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    User.__table__.create(engine)
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
            with urlopen(request, timeout=0.5) as response:  # noqa: S310
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not expose the authentication endpoint within five seconds.")


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
        }

        me_status, me_body = _request_json(
            "GET",
            f"{base_url}/api/v1/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )

    assert me_status == 200
    assert me_body == login_body["user"]


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
    with _running_server() as base_url:
        login_status, login_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "intern@itms.local", "password": "Intern@12345"},
        )
        assert login_status == 200
        access_token = login_body["access_token"]
        authorization = {"Authorization": f"Bearer {access_token}"}

        refresh_status, refresh_body = _request_json(
            "POST", f"{base_url}/api/v1/auth/refresh", headers=authorization
        )
        assert refresh_status == 200
        assert refresh_body["user"]["email"] == "intern@itms.local"

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

        relogin_status, relogin_body = _request_json(
            "POST",
            f"{base_url}/api/v1/auth/login",
            {"email": "intern@itms.local", "password": "Changed@12345"},
        )
        assert relogin_status == 200
        fresh_authorization = {"Authorization": f"Bearer {relogin_body['access_token']}"}

        logout_status, logout_body = _request_json(
            "POST", f"{base_url}/api/v1/auth/logout", headers=fresh_authorization
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
