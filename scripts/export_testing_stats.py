"""Write docs/evidence/user_testing_snapshot.md: tester counts and the date range, no names.

Usage: python scripts/export_testing_stats.py [--include-flagged] [--out PATH]
Reads the tester tables of DATABASE_URL (the demo's database) through the same code the judge's
Testing evidence screen uses. Judge and team devices are left out unless --include-flagged. Only
counts and dates are written: no nickname, hash, comment or per-person row.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "evidence" / "user_testing_snapshot.md"


def render(ev: dict[str, Any], generated: datetime) -> str:
    c = ev["cards"]
    lines = [
        "# User testing snapshot",
        "",
        f"Generated {generated.date().isoformat()} by `scripts/export_testing_stats.py` from the tester tables. Counts only: no names, hashes or comments.",
        "",
    ]
    if c["date_from"] is None:
        lines += [
            "Nothing has been collected yet. These tables fill only from testers who agreed to share.",
            "",
        ]
    else:
        lines += [f"Collected between {c['date_from']} and {c['date_to']}.", ""]

    def val(x: Any, suffix: str = "") -> str:
        return "none yet" if x is None else f"{x}{suffix}"

    lines += [
        "| Measure | Value |",
        "| --- | --- |",
        f"| Testers | {c['testers']} |",
        f"| Sessions | {c['sessions']} |",
        f"| Returning testers (more than one day) | {c['returning_testers']} |",
        f"| Roles tried per tester (average) | {val(c['roles_tried_avg'])} |",
        f"| Tours completed | {c['tours_completed']} |",
        f"| Feedback received | {c['feedback_received']} |",
        f"| Average rating (1 to 5) | {val(c['average_rating'])} |",
        f"| Share who used it offline | {val(None if c['offline_share'] is None else round(c['offline_share'] * 100), '%')} |",
        "",
        "## Testers by invite source",
        "",
    ]
    lines += [f"- {r['label']}: {r['testers']}" for r in ev["by_source"]] or ["- none yet"]
    lines += ["", "## Device class", ""]
    lines += [f"- {r['label']}: {r['testers']}" for r in ev["device_class"]] or ["- none yet"]
    lines += ["", "## Tour funnel (testers)", ""]
    lines += [f"- {r['stage']}: {r['testers']}" for r in ev["tour_funnel"]] or ["- none yet"]
    ex = ev["excluded"]
    lines += [
        "",
        "## Notes",
        "",
        f"- Judge and team devices are excluded from these counts ({ex['judge_devices']} judge, {ex['team_devices']} team devices)."
        if not ev["include_flagged"]
        else "- Judge and team devices are included in these counts.",
        f"- Recorded changes made from feedback: {len(ev['changes'])} (docs/YOU_SAID_WE_CHANGED.md).",
        '- Opt-in only; coarse data only; see README, "Tester stats".',
        "",
    ]
    return "\n".join(lines)


def snapshot(db: Session, include_flagged: bool = False, now: datetime | None = None) -> str:
    from services.tester.evidence import evidence

    return render(evidence(db, include_flagged), now or datetime.now(UTC))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-flagged", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from ai.config import load_env
    from services.api.db import make_engine
    from services.tester.models import ensure_tester_schema

    load_env()
    engine = make_engine()
    ensure_tester_schema(engine)
    with sessionmaker(engine, expire_on_commit=False)() as db:
        text = snapshot(db, args.include_flagged)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
