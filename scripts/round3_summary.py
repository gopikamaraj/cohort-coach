"""Summarise test round 3: System Usability Scale, "sounds like my class", completion.

Usage: python scripts/round3_summary.py [results.csv]
Reads docs/user-testing/round3-results.csv (one row per teacher, participant codes only) and writes
docs/evidence/round3_summary.json. Code computes every figure; nothing is typed by hand. With
fewer than 15 teachers the summary says so: "read as directional".
"""

from __future__ import annotations

import csv
import datetime
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "docs" / "user-testing" / "round3-results.csv"
OUT = ROOT / "docs" / "evidence" / "round3_summary.json"
SUS_COLUMNS = [f"sus_{i}" for i in range(1, 11)]


def sus_score(answers: list[int]) -> float:
    """Brooke's scoring: odd items score - 1, even items 5 - score, sum times 2.5 (0 to 100)."""
    if len(answers) != 10 or any(not 1 <= a <= 5 for a in answers):
        raise ValueError("a SUS response is ten answers, each 1 to 5")
    total = sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers))
    return total * 2.5


def summarise(rows: list[dict[str, str]]) -> dict[str, object]:
    if not rows:
        raise ValueError("no rows: add at least one teacher to the results file")
    scores = {r["participant"]: sus_score([int(r[c]) for c in SUS_COLUMNS]) for r in rows}
    realism = [int(r["realism_1to5"]) for r in rows if r.get("realism_1to5")]
    useful = [int(r["feedback_useful_1to5"]) for r in rows if r.get("feedback_useful_1to5")]
    finished = sum(
        r.get("finished_rehearsal", "").strip().lower() in {"y", "yes", "1", "true"} for r in rows
    )
    n = len(rows)
    return {
        "measure": "test_round_3",
        "source": "scripts/round3_summary.py",
        "date": datetime.date.today().isoformat(),
        "teachers": n,
        "sus_mean": round(statistics.mean(scores.values()), 1),
        "sus_by_participant": scores,
        "sounds_like_my_class_median": statistics.median(realism) if realism else "pending",
        "feedback_useful_median": statistics.median(useful) if useful else "pending",
        "finished_rehearsal": f"{finished} of {n}",
        "confidence_note": f"from {n} teachers, read as directional" if n < 15 else "",
    }


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else DEFAULT
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("participant")]
    summary = summarise(rows)
    OUT.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
