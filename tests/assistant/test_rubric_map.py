"""The rubric map is written from the code: every path exists, every status is honest, every slide
and video time it names exists, and the deck and video never claim more than it does."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.assistant import claims, rubric
from services.assistant.index import INDEX_DIR
from services.assistant.rubric import RubricError, parse, stricter

ROOT = Path(__file__).resolve().parents[2]
ROWS = rubric.load()


def exists(path: str) -> bool:
    return (ROOT / path.split("#")[0]).exists()


def test_every_criterion_and_bullet_has_at_least_one_row() -> None:
    by_crit: dict[str, set[str]] = {}
    for r in ROWS:
        by_crit.setdefault(r.criterion, set()).add(r.bullet)
    for crit, bullets in rubric.CRITERIA.items():
        assert crit in by_crit, crit
        assert set(bullets) <= by_crit[crit], (crit, set(bullets) - by_crit[crit])


def test_every_status_is_one_of_the_five_and_rows_are_unique() -> None:
    assert {r.status for r in ROWS} <= set(rubric.STATUSES)
    assert len({r.id for r in ROWS}) == len(ROWS) >= 25


def test_every_code_and_test_path_exists() -> None:
    for r in ROWS:
        for p in r.code + r.tests:
            if (
                p.endswith((".md", ".json", ".py", ".ts", ".tsx", ".yaml", ".mjs", ".css"))
                or "/" in p
            ):
                assert exists(p), f"{r.id}: {p} does not exist"


def test_every_row_says_how_to_check_it_and_what_it_cannot_do() -> None:
    for r in ROWS:
        assert r.claim and r.demo and r.limit, r.id
        assert r.code, f"{r.id} names no code"


def test_a_row_that_is_not_built_never_says_it_is() -> None:
    weak = [r for r in ROWS if r.status in ("Mock", "Roadmap")]
    assert weak
    for r in weak:
        assert r.limit not in ("", "—"), f"{r.id} must say what is missing"
        text = (r.claim + " " + r.limit).lower()
        assert "is live" not in text and "fully built" not in text, r.id


def test_slides_and_video_times_exist() -> None:
    sub = json.loads((INDEX_DIR / "submission.json").read_text(encoding="utf-8"))
    slides = {int(k) for k in sub["slides"]}
    for r in ROWS:
        for n in r.slides:
            assert n in slides, f"{r.id}: slide {n} does not exist"
        for t in r.video:
            assert t in sub["segments"], f"{r.id}: no video segment starts at {t}"


def test_every_timestamp_is_inside_the_video() -> None:
    sub = json.loads((INDEX_DIR / "submission.json").read_text(encoding="utf-8"))
    length = sub["video"]["length_s"]
    for t, seg in sub["segments"].items():
        start = int(t[:2]) * 60 + int(t[3:])
        assert 0 <= start < seg["end"] <= length, (t, seg, length)


def test_the_deck_and_video_do_not_claim_more_than_the_map() -> None:
    sub = json.loads((INDEX_DIR / "submission.json").read_text(encoding="utf-8"))
    rows = json.loads((INDEX_DIR / "rubric.json").read_text(encoding="utf-8"))
    assert all(not r["differs"] for r in rows), [
        (r["id"], r["differs"]) for r in rows if r["differs"]
    ]
    assert sub["forbidden"] == [], sub["forbidden"]  # "proven", "listened", "watched"


def test_a_claim_after_three_minutes_is_flagged_not_hidden() -> None:
    sub = json.loads((INDEX_DIR / "submission.json").read_text(encoding="utf-8"))
    assert isinstance(sub["late"], list)  # the list is the warning; it may be empty


def test_stricter_returns_the_weaker_status() -> None:
    assert stricter("Built", "Partly built") == "Partly built"
    assert stricter("Roadmap", "Built") == "Roadmap"
    assert stricter("Simulated", "Simulated") == "Simulated"


def test_the_parser_refuses_an_unknown_status_or_a_ragged_row() -> None:
    head = (
        "## Innovation (25 percent)\n\n| "
        + " | ".join(rubric.COLUMNS)
        + " |\n| "
        + " | ".join(["---"] * 11)
        + " |\n"
    )
    good = "| X1 | b | claim | Built | f | `a.py` | `t.py` | demo | limit | 1 | 00:00 |\n"
    assert len(parse(head + good)) == 1
    with pytest.raises(RubricError):
        parse(head + good.replace("Built", "Shipped"))
    with pytest.raises(RubricError):
        parse(head + "| X1 | b | claim |\n")
    with pytest.raises(RubricError):
        parse(head + good + good)


def test_claims_flag_a_stronger_word_in_the_deck_or_script() -> None:
    row = rubric.Row(
        "X", "c", "b", "claim", "Partly built", "f", ("a.py",), (), "d", "l", (7,), ("01:20",)
    )
    assert claims.mismatches(
        [row], {7: "The pilot is built and deployed."}, {"01:20": "Planned for later."}
    )
    assert claims.mismatches([row], {7: "Partly built."}, {"01:20": "Roadmap next."}) == []
    assert (
        claims.mismatches([row], {7: "Only the Practice Class needs a live connection."}, {}) == []
    )
    assert (
        claims.mismatches([row], {7: "Not yet built."}, {}) == []
    )  # "not built" is not a claim to be built
    row_built = rubric.Row("Y", "c", "b", "claim", "Built", "f", ("a.py",), (), "d", "l", (7,), ())
    assert (
        claims.mismatches([row_built], {7: "Simulated data, planned roadmap."}, {}) == []
    )  # weaker words are fine


def test_forbidden_words_and_late_claims() -> None:
    assert claims.forbidden(
        {3: "Teachers listened to the lesson."}, {"00:10": "This is proven."}
    ) == [
        "slide 3: listened",
        "video 00:10: proven",
    ]
    late = rubric.Row("L", "c", "b", "claim", "Built", "f", ("a.py",), (), "d", "l", (), ("03:05",))
    assert claims.late_claims([late]) == ["L first appears at 03:05"]
    early = rubric.Row(
        "E", "c", "b", "claim", "Built", "f", ("a.py",), (), "d", "l", (), ("01:05",)
    )
    assert claims.late_claims([early]) == []
