"""P09 T04: the Message Batches request builder, the cost estimate that prints first, and storing
drafts as review items. No network and no paid call."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai import config
from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.pricing import Usage, cost_usd
from ai.prompt_loader import load_prompt
from ai.schemas import TrackPart, Verdict
from services.api.db import Base, ReviewItem, make_engine
from services.content import drafting
from services.content.track import load_track
from tests.ai.test_c05_track_draft import GOOD, PASS
from tests.support_ai import FakeClient


@pytest.fixture
def db(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'content.sqlite'}")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session  # type: ignore[misc]


def test_one_request_per_part_and_language() -> None:
    track = load_track("sub-sfl.v1")
    requests = drafting.build_requests(track, ["hi", "en"])
    assert len(requests) == 14  # (6 lessons + the model lesson) x 2 languages
    ids = [r.custom_id for r in requests]
    assert len(set(ids)) == 14
    for custom_id in ids:  # the Batches API allows letters, digits, "_" and "-" up to 64
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", custom_id), custom_id
    assert "sub-sfl-v1_lesson_1_hi" in ids and "sub-sfl-v1_model_lesson_0_en" in ids


def test_every_request_shares_one_cached_system_block() -> None:
    track = load_track("sub-sfl.v1")
    requests = drafting.build_requests(track, ["en"])
    prompt = load_prompt("c05_track_draft")
    for r in requests:
        system = r.params["system"]
        assert system[0]["text"] == prompt.body
        assert system[0]["cache_control"] == {"type": "ephemeral"}
        assert r.params["model"] == config.model_for("MODEL_DRAFT")
        assert r.params["max_tokens"] == config.POLICIES["c05_track_draft"].max_tokens
    assert len({r.params["system"][0]["text"] for r in requests}) == 1


def test_each_request_asks_for_a_track_part_and_holds_no_class_number() -> None:
    track = load_track("sub-sfl.v1")
    request = drafting.build_requests(track, ["en"])[0]
    text = request.params["messages"][0]["content"][-1]["text"]
    assert "<facts>" in text and "class.count_showing" in text
    assert "%" not in text
    schema = request.params["output_config"]["format"]["schema"]
    assert set(schema["properties"]) == {"kind", "day", "script"}


def test_the_estimate_comes_from_the_price_file_and_applies_the_batch_discount() -> None:
    track = load_track("sub-sfl.v1")
    requests = drafting.build_requests(track, ["hi", "en"])
    est = drafting.estimate(requests, batch=True)
    expected = cost_usd(
        config.model_for("MODEL_DRAFT"), Usage(est.input_tokens, est.output_tokens), batch=True
    )
    assert est.usd == pytest.approx(expected)
    full = drafting.estimate(requests, batch=False)
    assert full.usd == pytest.approx(est.usd * 2)
    assert est.requests == 14 and est.usd > 0
    assert "USD" in est.summary() and "batch" in est.summary().lower()


def test_a_passing_draft_is_stored_as_a_pending_review_item(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    ctx = CallContext(
        mode="stub", client=FakeClient([TrackPart(kind="lesson", day=1, script=GOOD), PASS])
    )  # type: ignore[arg-type]
    draft = draft_part(track, "lesson", 1, "en", context=ctx)
    item = drafting.store_draft(db, draft, track)
    assert item is not None
    row = db.get(ReviewItem, item.item_id)
    assert row is not None
    assert (row.content_type, row.language, row.target_error, row.status) == (
        "track_draft",
        "en",
        "SUB-SFL",
        "pending",
    )
    assert row.content["script"] == GOOD and row.content["day"] == 1


def test_a_draft_blocked_by_code_is_not_stored(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    bad = TrackPart(kind="lesson", day=1, script=GOOD.replace("63 - 28 = 35", "63 - 28 = 36"))
    draft = draft_part(
        track,
        "lesson",
        1,
        "en",
        context=CallContext(mode="stub", client=FakeClient([bad])),  # type: ignore[arg-type]
    )
    assert drafting.store_draft(db, draft, track) is None
    assert db.execute(select(ReviewItem)).first() is None


def test_a_draft_the_checker_held_is_stored_with_its_reason_for_a_person(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    fail = Verdict(passed=False, failed_items=["tone"], reason_short="x", reason_for_user="harsh")
    ctx = CallContext(
        mode="stub", client=FakeClient([TrackPart(kind="lesson", day=1, script=GOOD), fail])
    )  # type: ignore[arg-type]
    draft = draft_part(track, "lesson", 1, "en", context=ctx)
    item = drafting.store_draft(db, draft, track)
    assert item is not None and item.content["status"] == "held_by_checker"
    assert item.badge == "none"


def test_the_same_part_is_not_queued_twice_while_one_is_pending(db: Session) -> None:
    track = load_track("sub-sfl.v1")

    def one() -> ReviewItem | None:
        ctx = CallContext(
            mode="stub", client=FakeClient([TrackPart(kind="lesson", day=1, script=GOOD), PASS])
        )  # type: ignore[arg-type]
        return drafting.store_draft(db, draft_part(track, "lesson", 1, "en", context=ctx), track)

    assert one() is not None
    assert one() is None
    assert len(list(db.execute(select(ReviewItem)).scalars())) == 1


def test_a_batch_result_is_validated_and_gated_like_a_synchronous_draft(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    ok = {
        "custom_id": "sub-sfl-v1_lesson_1_en",
        "text": TrackPart(kind="lesson", day=1, script=GOOD).model_dump_json(),
    }
    bad = {"custom_id": "sub-sfl-v1_lesson_2_en", "text": "not json"}
    ctx = CallContext(mode="stub", client=FakeClient([PASS]))  # type: ignore[arg-type]
    outcomes = drafting.ingest_results(db, track, [ok, bad], context=ctx)
    assert outcomes["sub-sfl-v1_lesson_1_en"] == "needs_review"
    assert outcomes["sub-sfl-v1_lesson_2_en"] == "no_output"
    assert len(list(db.execute(select(ReviewItem)).scalars())) == 1


def test_the_dry_run_prints_the_estimate_and_makes_no_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import batch_draft

    code = batch_draft.main(["--track", "sub-sfl.v1", "--languages", "hi,en", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Estimated cost" in out and "14 requests" in out and "USD" in out
