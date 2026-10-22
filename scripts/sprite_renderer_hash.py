"""Hash of the sprite renderer code (Python and TypeScript, not tests or data).

`tests/fixtures/sprite_renderer.sha256` holds the value recorded when the renderer was finished. A
new topic pack must not change it: the extensibility test fails if any renderer file differs.
Run with --write only when the renderer is deliberately changed (and log why in DECISIONS.md).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sprite_renderer.sha256"
DIRS = (ROOT / "services" / "api" / "sprites", ROOT / "apps" / "pwa" / "src" / "sprites")
SUFFIXES = {".py", ".ts", ".tsx"}


def renderer_files() -> list[Path]:
    files = [
        p
        for d in DIRS
        for p in d.rglob("*")
        if p.suffix in SUFFIXES and "test" not in p.name and "__pycache__" not in p.parts
    ]
    return sorted(files)


def renderer_hash() -> str:
    h = hashlib.sha256()
    for p in renderer_files():
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


if __name__ == "__main__":
    value = renderer_hash()
    if "--write" in sys.argv:
        FIXTURE.write_text(value + "\n", encoding="ascii")
    print(value, f"({len(renderer_files())} files)")
