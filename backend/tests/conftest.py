from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.db import session as db_session


class _RollbackSessionFactory:
    """Create test sessions inside one outer transaction, opened only when needed."""

    def __init__(self) -> None:
        self._connection: Connection | None = None
        self._factory: sessionmaker[Session] | None = None
        self._transaction = None

    def __call__(self, **kwargs: object) -> Session:
        if self._factory is None:
            self._connection = db_session.get_engine().connect()
            self._transaction = self._connection.begin()
            self._factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._connection,
                join_transaction_mode="create_savepoint",
            )
        return self._factory(**kwargs)

    def rollback(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()
        if self._connection is not None:
            self._connection.close()


@pytest.fixture(autouse=True)
def isolate_committed_database_changes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Prevent committed test rows from leaking into the application's database."""
    isolated_factory = _RollbackSessionFactory()
    monkeypatch.setattr(db_session, "_session_factory", isolated_factory)

    try:
        yield
    finally:
        isolated_factory.rollback()
