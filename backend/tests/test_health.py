import json
import socket
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).parents[1]


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _request_health(url: str) -> tuple[int, bytes]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=0.5) as response:  # noqa: S310
                return response.status, response.read()
        except URLError:
            time.sleep(0.1)
    raise AssertionError("Uvicorn did not expose the health endpoint within five seconds.")


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
        status, body = _request_health(f"http://127.0.0.1:{port}/api/v1/health")
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
