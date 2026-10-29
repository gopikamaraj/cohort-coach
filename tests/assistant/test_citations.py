"""Citations of three kinds resolve: the file at the deployed commit, the slide, the video time."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from services.assistant import answer, cite
from services.assistant.index import INDEX_DIR, Chunk
from services.assistant.scopes import scopes

SHA = "a" * 40
SUB = {
    "slides": {"7": "Real scenarios", "2": "The problem"},
    "deck_pdf": True,
    "video": {"url": "https://www.youtube.com/watch?v=abc123XYZ_-", "length_s": 175},
}


def chunk() -> Chunk:
    return Chunk(
        id="judge:docs/design/cohort-coach-design.md#practice-class:0",
        ns="judge",
        path="docs/design/cohort-coach-design.md",
        heading="Design > Practice Class",
        line=212,
        text="x",
    )


def test_a_file_citation_links_to_the_file_and_line_at_the_deployed_commit() -> None:
    c = cite.file_citation(chunk(), SHA)
    assert (
        c["type"] == "file" and c["label"] == "docs/design/cohort-coach-design.md, Practice Class"
    )
    assert c["url"] == f"{cite.REPO_URL}/blob/{SHA}/docs/design/cohort-coach-design.md#L212"
    assert cite.file_citation(chunk(), None)["url"].startswith(f"{cite.REPO_URL}/blob/main/")


def test_a_slide_citation_links_to_the_page_once_the_deck_is_in_the_repository() -> None:
    c = cite.slide_citation(7, SUB, SHA)
    assert c["label"] == "Deck slide 7" and c["title"] == "Real scenarios"
    assert (
        c["url"] == f"{cite.REPO_URL}/blob/{SHA}/docs/submission/deck.pdf#page=7"
        and c["note"] is None
    )
    draft = cite.slide_citation(7, {**SUB, "deck_pdf": False}, SHA)
    assert draft["url"] is None and "deck.pdf is not in the repository yet" in draft["note"]


def test_a_video_citation_links_to_the_start_time_in_seconds() -> None:
    c = cite.video_citation("01:20", SUB)
    assert c["label"] == "Video 01:20" and c["ts_start"] == 80
    q = parse_qs(urlparse(c["url"]).query)
    assert q["v"] == ["abc123XYZ_-"] and q["t"] == ["80s"]
    unset = cite.video_citation("01:20", {"video": {"url": None}})
    assert unset["url"] is None and "address is not set yet" in unset["note"]


def test_the_video_address_is_checked_and_an_old_start_time_is_replaced() -> None:
    assert cite.youtube_at("https://youtu.be/abc123", 5) == "https://youtu.be/abc123?t=5s"
    assert parse_qs(
        urlparse(cite.youtube_at("https://www.youtube.com/watch?v=a&t=999s", 61)).query
    )["t"] == ["61s"]
    for bad in (
        "http://www.youtube.com/watch?v=a",
        "https://evil.example/watch?v=a",
        "javascript:alert(1)",
    ):
        with pytest.raises(ValueError):
            cite.youtube_at(bad, 1)


def test_all_three_show_in_the_order_slide_video_file() -> None:
    cites = [
        cite.file_citation(chunk(), SHA),
        cite.video_citation("01:20", SUB),
        cite.slide_citation(7, SUB, SHA),
    ]
    assert (
        cite.label_line(cites)
        == "Deck slide 7 · Video 01:20 · docs/design/cohort-coach-design.md, Practice Class"
    )


def test_mmss_round_trips() -> None:
    assert (
        cite.mmss(80) == "01:20"
        and cite.to_seconds("01:20") == 80
        and cite.to_seconds("00:00") == 0
    )


def test_every_citation_in_every_pre_written_judge_answer_is_well_formed() -> None:
    lib = answer.library()
    for q in lib.banks["judge"]:
        a = answer.ask(scopes()["judge"], question_id=q.id)
        for s in a.sources:
            assert s["id"] and s["label"] and s["type"] in ("file", "slide", "video"), (q.id, s)
            if s["url"]:
                assert urlparse(s["url"]).scheme == "https", (q.id, s)
            if s["type"] == "file":
                assert s["path"] and ".." not in s["path"] and not s["path"].startswith("/")
            else:
                assert (
                    s["url"] is None and s["note"]
                )  # until the deck and video are final, it says so


def test_the_bundled_video_facts_are_consistent() -> None:
    sub = json.loads((INDEX_DIR / "submission.json").read_text(encoding="utf-8"))
    assert sub["video"]["length_s"] <= 180  # judges need not watch past 3:00
    assert sub["provisional"] is True  # until deck.pdf and the final video exist
    ends = [seg["end"] for seg in sub["segments"].values()]
    assert max(ends) <= sub["video"]["length_s"] and min(ends) > 0
