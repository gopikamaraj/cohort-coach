"""Initial JavaScript budget for the PWA: fail above 1 MB compressed, warn above 400 KB.

Usage: python scripts/bundle_size.py [--dist apps/pwa/dist]
"Initial" is what the first page load needs: every script and modulepreload that dist/index.html
names. Size is gzip level 9 of each file, the closest stand-in for what a host sends.
"""

from __future__ import annotations

import datetime
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAIL_BYTES = 1_000_000  # the design's budget: under 1 MB compressed
WARN_BYTES = 400_000
_REF = re.compile(r"""<(?:script|link)\b[^>]*?(?:src|href)=["']([^"']+\.js)["']""", re.IGNORECASE)


def initial_js(dist: Path) -> list[Path]:
    html = (dist / "index.html").read_text(encoding="utf-8")
    files: list[Path] = []
    for ref in _REF.findall(html):
        path = dist / ref.lstrip("/")
        if path.exists() and path not in files:
            files.append(path)
    return files


def compressed_size(path: Path) -> int:
    return len(gzip.compress(path.read_bytes(), compresslevel=9))


def check(dist: Path) -> tuple[int, list[tuple[str, int]]]:
    files = initial_js(dist)
    if not files:
        raise SystemExit(
            f"no initial JavaScript found in {dist / 'index.html'}: run the build first"
        )
    sizes = [(f.name, compressed_size(f)) for f in files]
    return sum(s for _, s in sizes), sizes


def main(argv: list[str]) -> int:
    dist = ROOT / "apps" / "pwa" / "dist"
    if "--dist" in argv:
        dist = Path(argv[argv.index("--dist") + 1])
    total, sizes = check(dist)
    if "--write" in argv:
        out = ROOT / "docs" / "evidence" / "bundle_size.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "measure": "pwa_initial_js",
            "source": "scripts/bundle_size.py --write",
            "date": datetime.date.today().isoformat(),
            "initial_js_gzip_bytes": total,
            "files": {name: size for name, size in sizes},
            "fail_above_bytes": FAIL_BYTES,
            "warn_above_bytes": WARN_BYTES,
            "within_budget": total <= FAIL_BYTES,
        }
        out.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    for name, size in sizes:
        print(f"  {name:<32} {size / 1000:8.1f} kB gzip")
    print(
        f"initial JS: {total / 1000:.1f} kB compressed "
        f"(fail above {FAIL_BYTES // 1000} kB, warn above {WARN_BYTES // 1000} kB)"
    )
    if total > FAIL_BYTES:
        print("FAIL: over the budget")
        return 1
    if total > WARN_BYTES:
        print("WARN: above the warning line")
    else:
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
