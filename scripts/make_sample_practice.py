"""Build the recorded sample rehearsal the app shows when practice is paused (budget reached).

Usage: python scripts/make_sample_practice.py
Reads docs/evidence/practice_session_live.json (a real live session on scripted, pretend lines)
and writes apps/pwa/public/sample-practice.json: only the lines and the feedback, in English.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "evidence" / "practice_session_live.json"
OUT = ROOT / "apps" / "pwa" / "public" / "sample-practice.json"


def build(session: dict) -> dict:  # type: ignore[type-arg]
    return {
        "source": "docs/evidence/practice_session_live.json",
        "language": session["language"],
        "scenario": session["scenario"],
        "turns": [
            {
                "turn": i + 1,
                "teacher": t["layers"]["input"]["teacher_text"]
                or f"[tapped {t['layers']['input']['material']}]",
                "speaker": t["speaker"],
                "child": t["child_text"],
            }
            for i, t in enumerate(session["turns"])
        ],
        "feedback": {
            "strengths": [
                {"comment": s["comment"], "quote": s["quote"]}
                for s in session["feedback"]["strengths"]
            ],
            "try_next": {"suggestion": session["feedback"]["try_next"]["suggestion"]},
        },
    }


def main() -> int:
    data = build(json.loads(SRC.read_text(encoding="utf-8")))
    OUT.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT.relative_to(ROOT)} ({len(data['turns'])} turns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
