import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from data.synthetic.block import generate_block
from services.api.db import (
    Assignment,
    Base,
    ClassRoom,
    ClassTermCount,
    Cohort,
    School,
)
from services.api.seed import seed_database

ROOT = Path(__file__).resolve().parents[2]
BLOCK_PATH = ROOT / "data" / "synthetic" / "block_T1T2.json"


@pytest.fixture(scope="module")
def block() -> dict[str, Any]:
    return generate_block()


@pytest.fixture()
def session() -> Session:  # type: ignore[misc]
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_seed_writes_every_table(session: Session, block: dict[str, Any]) -> None:
    seed_database(session, block)
    assert session.scalar(select(func.count()).select_from(School)) == 40
    assert session.scalar(select(func.count()).select_from(ClassRoom)) == 120
    assert session.scalar(select(func.count()).select_from(ClassTermCount)) == 240
    assert session.scalar(select(func.count()).select_from(Assignment)) == len(block["assignments"])
    assert session.scalar(select(func.count()).select_from(Cohort)) == len(block["cohorts"])


def test_every_row_is_marked_simulated(session: Session, block: dict[str, Any]) -> None:
    seed_database(session, block)
    for model in (School, ClassRoom, ClassTermCount, Assignment, Cohort):
        total = session.scalar(select(func.count()).select_from(model))
        flagged = session.scalar(select(func.count()).select_from(model).where(model.simulated))
        assert total == flagged and total > 0


def test_the_schema_stores_class_counts_only(session: Session) -> None:
    columns = {
        t: {c["name"] for c in inspect(session.get_bind()).get_columns(t)}
        for t in inspect(session.get_bind()).get_table_names()
    }
    banned = ("child", "roll", "answer", "photo", "pupil", "student")
    class_level = {"children_checked", "children_showing"}  # counts about a class, not a child
    for table, cols in columns.items():
        offenders = [c for c in cols - class_level if any(b in c.lower() for b in banned)]
        assert not offenders, (table, offenders)
    assert {"children_checked", "counts"} <= columns["class_term_count"]


def test_seeding_twice_replaces_rather_than_duplicates(
    session: Session, block: dict[str, Any]
) -> None:
    seed_database(session, block)
    seed_database(session, block)
    assert session.scalar(select(func.count()).select_from(ClassTermCount)) == 240


def test_stored_counts_round_trip(session: Session, block: dict[str, Any]) -> None:
    seed_database(session, block)
    row = session.scalars(select(ClassTermCount).where(ClassTermCount.term == "T2")).first()
    assert row is not None
    assert row.counts == block["terms"]["T2"]["classes"][row.class_id]["counts"]


def test_committed_block_file_is_fresh(block: dict[str, Any]) -> None:
    """Fails if the generator or its config changed without `python tasks.py seed`."""
    committed = json.loads(BLOCK_PATH.read_text(encoding="utf-8"))
    assert committed["data_hash"] == block["data_hash"]
    assert committed == block


def test_seed_command_check_passes_and_prints_the_hash() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tasks.py"), "seed", "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "data hash" in result.stdout and "ok" in result.stdout
