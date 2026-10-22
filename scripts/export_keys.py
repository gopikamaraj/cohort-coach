"""Write (or check) the generated answer keys and golden diagnosis cases.

Usage: python scripts/export_keys.py [--check]
  default  write apps/pwa/src/generated/answer_keys.json and tests/fixtures/diagnosis_cases.json
  --check  exit 1 if either committed file differs from what the engine would write now
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.export_keys import (  # noqa: E402
    build_answer_keys,
    build_diagnosis_cases,
    build_stage_cases,
    render,
)
from engine.forms import PILOT_FORMS  # noqa: E402
from services.api.sprites.golden import golden  # noqa: E402

TARGETS = {
    ROOT / "apps/pwa/src/generated/answer_keys.json": lambda: render(
        build_answer_keys(PILOT_FORMS)
    ),
    ROOT / "tests/fixtures/diagnosis_cases.json": lambda: render(build_diagnosis_cases()),
    ROOT / "tests/fixtures/stage_cases.json": lambda: render(build_stage_cases()),
    ROOT / "tests/fixtures/sprite_golden.json": lambda: render(golden()),
}


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = 0
    for path, make in TARGETS.items():
        text = make()
        rel = path.relative_to(ROOT)
        if check:
            same = path.exists() and path.read_text(encoding="utf-8") == text
            print(f"{'ok   ' if same else 'STALE'} {rel}")
            stale += not same
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {rel} ({len(text):,} bytes)")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
