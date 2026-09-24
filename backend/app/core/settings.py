from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

API_PREFIX = "/api/v1"


def _origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    environment: str
    cors_origins: tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("ITMS_ENVIRONMENT", "development"),
        cors_origins=_origins(os.getenv("ITMS_CORS_ORIGINS", "http://localhost:4200")),
    )
