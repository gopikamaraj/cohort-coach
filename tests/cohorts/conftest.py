from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine


@pytest.fixture
def factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'cohorts.sqlite'}")
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def db(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as s:
        yield s
