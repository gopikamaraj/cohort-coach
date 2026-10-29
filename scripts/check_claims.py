"""List where the deck or the video script claims more than docs/RUBRIC_MAP.md allows.

    python scripts/check_claims.py            list every mismatch (exit 0)
    python scripts/check_claims.py --strict   exit 1 if there is any mismatch or forbidden word

Reads the bundled facts (docs/submission/slides.md and video_script.md, as chunked by the index),
so run `python scripts/build_assistant_index.py` first. If the deck and the rubric map disagree, the
judge guide reports the stricter status and says the deck or video differs, so fix the source that
is wrong: change the deck or the video, or change the row's status honestly.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.assistant import claims, index, rubric  # noqa: E402


def collect() -> tuple[list[rubric.Row], dict[int, str], dict[str, str]]:
    built = index.build()
    judge = built.chunks.get("judge", [])
    slides = {
        c.slide_no: f"{c.heading} {c.text}" for c in judge if c.kind == "slide" and c.slide_no
    }
    segments = {
        f"{(c.ts_start or 0) // 60:02d}:{(c.ts_start or 0) % 60:02d}": f"{c.section} {c.text}"
        for c in judge
        if c.kind == "video"
    }
    return rubric.load(), slides, segments


def main(argv: list[str]) -> int:
    rows, slides, segments = collect()
    bad = claims.mismatches(rows, slides, segments)
    never = claims.forbidden(slides, segments)
    late = claims.late_claims(rows)
    for m in bad:
        print(
            f"MISMATCH {m.row}: {m.where} says '{m.word}' ({m.says}) but the row is {m.row_status}"
        )
    for f in never:
        print(f"FORBIDDEN {f}")
    for line in late:
        print(f"LATE {line} (after 03:00; reviewers need not watch that far)")
    print(
        f"{len(rows)} rows, {len(slides)} slides, {len(segments)} video segments: "
        f"{len(bad)} mismatches, {len(never)} forbidden words, {len(late)} late claims"
    )
    return 1 if "--strict" in argv and (bad or never) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
