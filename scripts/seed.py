"""Build the simulated block, write data/synthetic/block_T1T2.json and seed the database.

Usage: python scripts/seed.py [--check] [--no-db]
  default   write the JSON, seed DATABASE_URL (default sqlite:///./dev.sqlite), print the data hash
  --check   write nothing; exit 1 if the committed JSON differs from what the generator makes now
  --no-db   skip the database
Everything produced is simulated. Run it twice: the data hash is the same.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from data.synthetic.block import generate_block  # noqa: E402
from services.api.db import Base  # noqa: E402
from services.api.seed import seed_database  # noqa: E402

BLOCK_PATH = ROOT / "data" / "synthetic" / "block_T1T2.json"


def render(block: dict[str, object]) -> str:
    return json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    block = generate_block()
    text = render(block)
    print(f"data hash {block['data_hash']}")
    if "--check" in argv:
        same = BLOCK_PATH.exists() and BLOCK_PATH.read_text(encoding="utf-8") == text
        print(f"{'ok   ' if same else 'STALE'} {BLOCK_PATH.relative_to(ROOT)}")
        return 0 if same else 1
    BLOCK_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {BLOCK_PATH.relative_to(ROOT)} ({len(text):,} bytes)")
    if "--no-db" not in argv:
        url = os.environ.get("DATABASE_URL", "sqlite:///./dev.sqlite")
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            seed_database(session, block)
        print(f"seeded {url.split('@')[-1]}: {len(block['classes'])} classes, 2 terms (simulated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
