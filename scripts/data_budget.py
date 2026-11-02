"""Worst-case data per teacher per 3-week track, from the settings the code enforces.

Usage: python scripts/data_budget.py [--out docs/evidence/data_budget.json]
This is a COMPUTED bound, not a measured journey: it multiplies the limits the code enforces (the
lesson length cap and the voice bit rate used by `services.content.publish`, the photo size the
phone aims for) by the number of items a teacher meets, and adds the measured first-load size of
the web app from docs/evidence/bundle_size.json. A measured run on a real phone and on Slow 3G is
a human job (docs/build/PROGRESS.md) and is not claimed here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.content.lessons_view import MAX_LESSON_SECONDS  # noqa: E402
from services.content.model_run import KBPS as MODEL_RUN_KBPS  # noqa: E402
from services.content.publish import KBPS  # noqa: E402

TARGET_MB = 10.0
SHEET_KB = 80  # the phone shrinks a sheet photo to about 80 KB (CLAUDE.md section 9)
SHEETS = 40  # a class of up to 40 children
LESSONS = 6
MODEL_RUN_SECONDS = 180  # the model run is about 3 minutes (cut in P09: counted as if built)
PRACTICE_TEXT_KB = 50  # a text-mode Practice Class session
PRACTICE_SESSIONS = 6
PRACTICE_VOICE_MB = 1.0  # a voice session, if she uses voice every time
MB = 1_000_000


def first_load_mb() -> float:
    path = ROOT / "docs" / "evidence" / "bundle_size.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("initial_js_gzip_bytes", "initial_js_compressed_bytes", "gzip_bytes", "total_gzip"):
        if key in data:
            return float(data[key]) / MB
    return float(data.get("initial_kb_gzip", 0)) * 1000 / MB


def budget() -> dict[str, Any]:
    lesson_mb = MAX_LESSON_SECONDS * KBPS * 1000 / 8 / MB  # worst case: every lesson at the cap
    rows = {
        "web app first load (measured, compressed)": round(first_load_mb(), 3),
        "check sheets (40 photos at about 80 KB)": round(SHEETS * SHEET_KB * 1000 / MB, 3),
        f"{LESSONS} voice lessons at the {MAX_LESSON_SECONDS // 60}-minute cap, {KBPS} kbps": round(
            LESSONS * lesson_mb, 3
        ),
        f"model run (about 3 minutes, {MODEL_RUN_KBPS} kbps)": round(
            MODEL_RUN_SECONDS * MODEL_RUN_KBPS * 1000 / 8 / MB, 3
        ),
        f"{PRACTICE_SESSIONS} Practice Class sessions in text mode": round(
            PRACTICE_SESSIONS * PRACTICE_TEXT_KB * 1000 / MB, 3
        ),
    }
    text_total = round(sum(rows.values()), 3)
    voice_extra = round(PRACTICE_SESSIONS * (PRACTICE_VOICE_MB - PRACTICE_TEXT_KB * 1000 / MB), 3)
    return {
        "kind": "computed worst case, not a measured journey",
        "target_mb": TARGET_MB,
        "rows_mb": rows,
        "total_mb_text_practice": text_total,
        "total_mb_if_every_session_uses_voice": round(text_total + voice_extra, 3),
        "within_target_text": text_total < TARGET_MB,
        "within_target_voice": text_total + voice_extra < TARGET_MB,
        "settings": {
            "lesson_seconds_cap": MAX_LESSON_SECONDS,
            "voice_kbps": KBPS,
            "sheet_kb": SHEET_KB,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=str(ROOT / "docs" / "evidence" / "data_budget.json"))
    args = p.parse_args(argv)
    result = budget()
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
