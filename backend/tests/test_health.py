import json
import socket
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).parents[1]


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _request_endpoint(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    deadline = time.monotonic() + 5
    req = Request(url, headers=headers or {})
    while time.monotonic() < deadline:
        try:
            with urlopen(req, timeout=0.5) as response:  # noqa: S310
                return response.status, response.read()
        except URLError as e:
            if hasattr(e, "code"):
                return e.code, e.read()
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not respond within five seconds.")


# Test 1: Giữ nguyên test health check ban đầu
def test_health_returns_service_status() -> None:
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
        status, body = _request_endpoint(f"http://127.0.0.1:{port}/api/v1/health")
    finally:
        server.terminate()
        with suppress(subprocess.TimeoutExpired):
            server.wait(timeout=3)
        if server.poll() is None:
            server.kill()

    assert status == 200
    assert json.loads(body) == {
        "status": "ok",
        "service": "itms-backend",
        "environment": "development",
    }


# Test 2: RBAC - Cho phép ADMIN truy cập
def test_rbac_admin_allow() -> None:
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
        status, body = _request_endpoint(
            f"http://127.0.0.1:{port}/api/v1/protected-route",
            headers={"X-User-Role": "ADMIN"},
        )
    finally:
        server.terminate()
        with suppress(subprocess.TimeoutExpired):
            server.wait(timeout=3)

    assert status == 200
    assert json.loads(body) == {"message": "Welcome Admin!"}


# Test 3: RBAC - Chặn INTERN truy cập (Trả về HTTP 403 Forbidden)
def test_rbac_intern_deny() -> None:
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
        status, _ = _request_endpoint(
            f"http://127.0.0.1:{port}/api/v1/protected-route",
            headers={"X-User-Role": "INTERN"},
        )
    finally:
        server.terminate()
        with suppress(subprocess.TimeoutExpired):
            server.wait(timeout=3)

    assert status == 403


# Test 4: Core Fallback - Đảm bảo Core vẫn chạy khi Email/AI lỗi
def test_core_fallback_when_external_service_fails() -> None:
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
        status, body = _request_endpoint(
            f"http://127.0.0.1:{port}/api/v1/core-service?service_status=fail"
        )
    finally:
        server.terminate()
        with suppress(subprocess.TimeoutExpired):
            server.wait(timeout=3)

    assert status == 200
    assert json.loads(body)["core_status"] == "operational"
