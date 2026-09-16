from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

API_PREFIX = "/api/v1"
JWT_SECRET_PLACEHOLDER = "<replace-with-a-unique-secret>"
MIN_JWT_SECRET_BYTES = 32


def _origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def _jwt_secret(value: str | None) -> str | None:
    if value in (None, JWT_SECRET_PLACEHOLDER):
        return None
    if len(value.encode()) < MIN_JWT_SECRET_BYTES:
        return None
    return value


@dataclass(frozen=True)
class Settings:
    environment: str
    cors_origins: tuple[str, ...]
    jwt_issuer: str
    jwt_secret: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("ITMS_ENVIRONMENT", "development"),
        cors_origins=_origins(os.getenv("ITMS_CORS_ORIGINS", "http://localhost:4200")),
        jwt_issuer=os.getenv("ITMS_JWT_ISSUER", "itms-backend"),
        jwt_secret=_jwt_secret(os.getenv("ITMS_JWT_SECRET")),
    )
