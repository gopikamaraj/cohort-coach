"""Citations of three kinds, each with a way to check it.

* file: a repository file and heading, linked at the deployed commit (`#L<line>`);
* slide: a deck slide, linked to deck.pdf#page=N once the final deck is in the repository;
* video: a time in the video, linked to the YouTube address with the start time in seconds.

A judge answer can show all three, in this order:
"Deck slide 7 · Video 01:20 · docs/design/cohort-coach-design.md, Practice Class".
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from services.assistant.index import Chunk

REPO_URL = "https://github.com/gopikamaraj/cohort-coach"


def mmss(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def to_seconds(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def youtube_at(url: str, seconds: int) -> str:
    """The address with the start time set (t=<n>s), keeping the video id."""
    parts = urlparse(url)
    if parts.scheme != "https" or parts.netloc not in {
        "www.youtube.com",
        "youtube.com",
        "youtu.be",
        "m.youtube.com",
    }:
        raise ValueError("not a YouTube address")
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "t"] + [("t", f"{seconds}s")]
    return urlunparse(parts._replace(query=urlencode(query)))


def short_heading(heading: str) -> str:
    return heading.split(" > ")[-1] if heading else ""


def file_citation(chunk: Chunk, sha: str | None) -> dict[str, Any]:
    ref = sha or "main"
    return {
        "type": "file",
        "id": chunk.id,
        "label": f"{chunk.path}, {short_heading(chunk.heading)}" if chunk.heading else chunk.path,
        "path": chunk.path,
        "heading": chunk.heading,
        "line": chunk.line,
        "url": f"{REPO_URL}/blob/{ref}/{chunk.path}#L{chunk.line}",
    }


def slide_citation(n: int, submission: dict[str, Any], sha: str | None) -> dict[str, Any]:
    title = submission.get("slides", {}).get(str(n), "")
    pdf = bool(submission.get("deck_pdf"))
    return {
        "type": "slide",
        "id": f"slide-{n}",
        "label": f"Deck slide {n}",
        "slide_no": n,
        "title": title,
        "url": f"{REPO_URL}/blob/{sha or 'main'}/docs/submission/deck.pdf#page={n}"
        if pdf
        else None,
        "note": None
        if pdf
        else "deck.pdf is not in the repository yet; the number follows the deck source",
    }


def video_citation(t: str, submission: dict[str, Any]) -> dict[str, Any]:
    s = to_seconds(t)
    url = (submission.get("video") or {}).get("url")
    return {
        "type": "video",
        "id": f"video-{t}",
        "label": f"Video {t}",
        "ts_start": s,
        "url": youtube_at(url, s) if url else None,
        "note": None
        if url
        else "the video address is not set yet; the time follows the shooting script",
    }


def label_line(citations: list[dict[str, Any]]) -> str:
    order = {"slide": 0, "video": 1, "file": 2}
    return " · ".join(c["label"] for c in sorted(citations, key=lambda c: order[c["type"]]))
