from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _sqlalchemy_url(database_url: str) -> str:
    """Select psycopg v3 when a provider supplies a generic PostgreSQL URL."""
    if database_url.startswith("postgres://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgres://')}"
    if database_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgresql://')}"
    return database_url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. Set ITMS_DATABASE_URL or DATABASE_URL."
            )
        _engine = create_engine(
            _sqlalchemy_url(settings.database_url),
            echo=settings.db_echo,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _session_factory


def get_db() -> Generator[Session, Any]:
    """FastAPI dependency that yields a SQLAlchemy database session."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
