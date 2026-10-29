"""Shared fixtures for the chat tests: a database, an active cohort with five members, a coach and
a mentor, and approved lesson material the draft can cite."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from services.api.cohorts import lifecycle, thread
from services.api.db import Base, ContentVersion, ReviewItem, make_engine

COACH = "coach-demo"
MENTOR = "mentor-demo"
OFFICER = "officer-demo"
TEACHERS = [f"t-chat{i:013d}" for i in range(5)]


@dataclass
class World:
    db: Session
    cohort_id: str
    teacher: str
    other_teacher: str


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'chat.sqlite'}")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def world(db: Session) -> World:
    cohort = lifecycle.create(
        db,
        error="SUB-SFL",
        coach_id=COACH,
        mentor_ids=[MENTOR],
        officer_id=OFFICER,
        school_count=7,
        cohort_id="co-chat-test",
    )
    lifecycle.transition(db, cohort.id, "active", role="officer", actor=OFFICER)
    for t in TEACHERS:
        thread.join(db, cohort.id, t)
    return World(db, cohort.id, TEACHERS[0], TEACHERS[1])


LESSON_1 = (
    "Ask the child how she got her answer. Listen before you say if it is right. "
    "Then show it with bundles of ten sticks."
)
LESSON_4 = (
    "Open a bundle to get ten loose sticks. Now take away 9 loose sticks. "
    "Then take away 2 bundles. Check it by adding back. 63 - 28 = 35. "
    "Today {{class.count_showing}} of {{class.children_checked}} children made this mistake."
)
LESSON_1_HI = "बच्चे से पूछें कि उसने जवाब कैसे निकाला। जवाब सही है या नहीं, यह बाद में बताएँ।"


def add_item(
    db: Session, language: str, kind: str, day: int, script: str, status: str = "approved"
) -> str:
    item = ReviewItem(
        item_id=uuid.uuid4().hex,
        content_type="track_draft",
        language=language,
        target_error="SUB-SFL",
        content={"kind": kind, "day": day, "script": script, "track_id": "sub-sfl.v1"},
        badge="checked_reviewed" if status == "approved" else "checked",
        status=status,
    )
    db.add(item)
    db.commit()
    return item.item_id


def switch_on(
    db: Session, parts: dict[str, dict[str, str]], *, error: str = "SUB-SFL", status: str = "active"
) -> ContentVersion:
    """A track version whose parts are listed per language: {"en": {"lesson_1": item_id}}."""
    v = ContentVersion(
        id=uuid.uuid4().hex,
        content_type="track",
        content_id="sub-sfl.v1",
        version=(db.execute(select(func.max(ContentVersion.version))).scalar() or 0) + 1,
        status=status,
        body={
            "track_id": "sub-sfl.v1",
            "error": error,
            "languages": {
                lang: {k: {"item_id": i} for k, i in items.items()} for lang, items in parts.items()
            },
        },
        content_hash="x" * 64,
        created_by="test",
    )
    db.add(v)
    db.commit()
    return v


@pytest.fixture
def material(world: World) -> dict[str, str]:
    """Approved lessons in English (1 and 4) and Hindi (1), switched on."""
    db = world.db
    ids = {
        "en1": add_item(db, "en", "lesson", 1, LESSON_1),
        "en4": add_item(db, "en", "lesson", 4, LESSON_4),
        "hi1": add_item(db, "hi", "lesson", 1, LESSON_1_HI),
    }
    switch_on(
        db,
        {"en": {"lesson_1": ids["en1"], "lesson_4": ids["en4"]}, "hi": {"lesson_1": ids["hi1"]}},
    )
    return ids
