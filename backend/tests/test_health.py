import json
import os
import socket
import subprocess
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt

PROJECT_ROOT = Path(__file__).parents[1]
JWT_SECRET = "test-secret-that-is-at-least-thirty-two-bytes-long"
JWT_ISSUER = "itms-backend"


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _request_endpoint(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    deadline = time.monotonic() + 5
    request = Request(url, headers=headers or {})
    while time.monotonic() < deadline:
        try:
            with urlopen(request, timeout=0.5) as response:  # noqa: S310
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()
        except URLError:
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not expose the health endpoint within five seconds.")


def _access_token(role: str, *, secret: str = JWT_SECRET) -> str:
    return jwt.encode(
        {
            "sub": "user-test-id",
            "role": role,
            "iss": JWT_ISSUER,
            "exp": datetime.now(UTC) + timedelta(minutes=1),
        },
        secret,
        algorithm="HS256",
    )


def _start_server(jwt_secret: str = JWT_SECRET) -> tuple[subprocess.Popen[bytes], str]:
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
        env={**os.environ, "ITMS_JWT_SECRET": jwt_secret},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return server, f"http://127.0.0.1:{port}/api/v1"


def _stop_server(server: subprocess.Popen[bytes]) -> None:
    server.terminate()
    with suppress(subprocess.TimeoutExpired):
        server.wait(timeout=3)
    if server.poll() is None:
        server.kill()


def test_health_returns_service_status() -> None:
    server, base_url = _start_server()
    try:
        status, body = _request_endpoint(f"{base_url}/health")
    finally:
        _stop_server(server)

    assert status == 200
    assert json.loads(body) == {
        "status": "ok",
        "service": "itms-backend",
        "environment": "development",
    }


def test_protected_route_requires_bearer_token() -> None:
    server, base_url = _start_server()
    try:
        status, _ = _request_endpoint(
            f"{base_url}/protected-route",
            headers={"X-User-Role": "ADMIN"},
        )
    finally:
        _stop_server(server)

    assert status == 401


def test_protected_route_rejects_placeholder_jwt_secret() -> None:
    server, base_url = _start_server("<replace-with-a-unique-secret>")
    try:
        status, _ = _request_endpoint(
            f"{base_url}/protected-route",
            headers={"Authorization": "Bearer ignored"},
        )
    finally:
        _stop_server(server)

    assert status == 503


def test_protected_route_rejects_forged_token() -> None:
    forged_token = _access_token(
        "ADMIN",
        secret="forged-secret-that-is-at-least-thirty-two-bytes-long",
    )
    server, base_url = _start_server()
    try:
        status, _ = _request_endpoint(
            f"{base_url}/protected-route",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
    finally:
        _stop_server(server)

    assert status == 401


def test_protected_route_denies_authenticated_intern() -> None:
    server, base_url = _start_server()
    try:
        status, _ = _request_endpoint(
            f"{base_url}/protected-route",
            headers={"Authorization": f"Bearer {_access_token('INTERN')}"},
        )
    finally:
        _stop_server(server)

    assert status == 403


def test_protected_route_allows_authenticated_admin() -> None:
    server, base_url = _start_server()
    try:
        status, body = _request_endpoint(
            f"{base_url}/protected-route",
            headers={"Authorization": f"Bearer {_access_token('ADMIN')}"},
        )
    finally:
        _stop_server(server)

    assert status == 200
    assert json.loads(body) == {"message": "Welcome Admin!"}
