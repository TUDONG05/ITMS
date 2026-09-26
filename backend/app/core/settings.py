from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

API_PREFIX = "/api/v1"
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
AVATAR_UPLOAD_DIR = UPLOAD_DIR / "avatars"
AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _load_env_file() -> None:
    for candidate in (
        Path("environment.local"),
        Path("../environment.local"),
        Path(__file__).resolve().parents[3] / "environment.local",
    ):
        if candidate.is_file():
            try:
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
            break


def _origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    environment: str
    cors_origins: tuple[str, ...]
    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    access_token_ttl_seconds: int
    database_url: str | None = None
    db_echo: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None


@lru_cache
def get_settings() -> Settings:
    _load_env_file()
    db_url = os.getenv("ITMS_DATABASE_URL") or os.getenv("DATABASE_URL")
    db_echo_raw = os.getenv("ITMS_DB_ECHO", "false").lower()
    return Settings(
        environment=os.getenv("ITMS_ENVIRONMENT", "development"),
        cors_origins=_origins(os.getenv("ITMS_CORS_ORIGINS", "http://localhost:4200")),
        jwt_secret=os.getenv("ITMS_JWT_SECRET", "development-only-secret-change-me"),
        jwt_issuer=os.getenv("ITMS_JWT_ISSUER", "itms-backend"),
        jwt_audience=os.getenv("ITMS_JWT_AUDIENCE", "itms-web-client"),
        access_token_ttl_seconds=int(os.getenv("ITMS_ACCESS_TOKEN_TTL_SECONDS", "900")),
        database_url=db_url,
        db_echo=db_echo_raw in ("true", "1", "yes"),
        smtp_host=os.getenv("ITMS_SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("ITMS_SMTP_PORT", "465")),
        smtp_username=os.getenv("ITMS_SMTP_USERNAME"),
        smtp_password=os.getenv("ITMS_SMTP_PASSWORD"),
        smtp_from_email=os.getenv("ITMS_SMTP_FROM_EMAIL"),
    )
