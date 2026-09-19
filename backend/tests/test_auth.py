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

from app.core.security import hash_password
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
        except URLError:
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
