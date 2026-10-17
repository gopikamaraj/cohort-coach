"""Export JSON Schemas for the Practice Class content files to content/schemas/.

Usage: python scripts/export_content_schemas.py [--check]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.practice.content import SCHEMAS, schema_json  # noqa: E402

OUT = ROOT / "content" / "schemas"


def main(argv: list[str]) -> int:
    bad = 0
    for name in SCHEMAS:
        path = OUT / f"{name}.schema.json"
        text = schema_json(name)
        if "--check" in argv:
            if not path.exists() or path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
                print(f"out of date: {path.relative_to(ROOT)}")
                bad = 1
            else:
                print(f"ok    {path.relative_to(ROOT)}")
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(ROOT)}")
    return bad


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
