# ruff: noqa: E501
"""The shared database session dependency. Lives here (not in profiles.py) so the identity module, which
profiles.py itself needs, can depend on it without an import loop. `from services.api.profiles import get_session`
still works and is the same function, so test overrides keep applying."""

from __future__ import annotations

from collections.abc import Iterator
from functools import cache

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine


@cache
def _factory() -> sessionmaker[Session]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    from services.modules import migrate

    migrate.widen_answer_column(engine)
    migrate.widen_profile_form(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        migrate.tried_to_worked(db)  # rows made before "tried" became "worked"
        from services.api.seed import fix_sequences

        fix_sequences(db)  # Postgres: counters past any rows copied in with their own ids
    return factory


def get_session() -> Iterator[Session]:
    with _factory()() as s:
        yield s


SESSION = Depends(get_session)
