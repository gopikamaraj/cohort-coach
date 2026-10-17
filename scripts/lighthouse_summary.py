"""Reduce a Lighthouse JSON report to the figures the docs cite (lighthouse_mobile.json).

Usage (repo root; PWA built and `npx vite preview --port 4173` running):
  CHROME_PATH=<chrome> npx lighthouse http://localhost:4173/ \
      --only-categories=performance,accessibility,best-practices \
      --chrome-flags="--headless=new --no-sandbox" --output=json --output-path=apps/pwa/lh.json
  python scripts/lighthouse_summary.py apps/pwa/lh.json
Lighthouse's default mobile profile is the throttled one (emulated phone, simulated slow 4G, CPU
slowed 4x). Lighthouse 12 and later have no PWA score; installability and offline behaviour are
checked by the Playwright tests instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "evidence" / "lighthouse_mobile.json"
METRICS = (
    "first-contentful-paint",
    "largest-contentful-paint",
    "total-blocking-time",
    "cumulative-layout-shift",
    "speed-index",
    "interactive",
)


def summarise(report: dict[str, object]) -> dict[str, object]:
    cats: dict[str, dict[str, object]] = report["categories"]  # type: ignore[assignment]
    audits: dict[str, dict[str, object]] = report["audits"]  # type: ignore[assignment]
    settings: dict[str, object] = report["configSettings"]  # type: ignore[assignment]
    emulated: dict[str, object] = settings["screenEmulation"]  # type: ignore[assignment]
    return {
        "measure": "lighthouse_mobile",
        "source": "scripts/lighthouse_summary.py on a Lighthouse JSON report",
        "date": str(report["fetchTime"])[:10],
        "lighthouse_version": report["lighthouseVersion"],
        "url": report["requestedUrl"],
        "form_factor": settings["formFactor"],
        "throttling_method": settings["throttlingMethod"],
        "screen": {"width": emulated["width"], "height": emulated["height"]},
        "scores_0_to_100": {k: round(float(v["score"]) * 100) for k, v in cats.items()},  # type: ignore[arg-type]
        "metrics": {k: audits[k]["displayValue"] for k in METRICS},
        "note": "One run on one machine; read as directional. No PWA category in Lighthouse 12+.",
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    report = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(summarise(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
