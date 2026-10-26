"""Rejections waiting to become checker examples.

A coach's rejection writes the excerpt and the structured reason to `content/rejections/pending/`.
Nothing there reaches call 7. Someone curates it: "use as checker example" promotes a file to
`approved/` (`promote`), which is what ai/guard/rejections.py reads into call 7's prompt. This
keeps one careless click from teaching the checker the wrong lesson.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai.guard.rejections import RejectionReason

PENDING_DIR = Path(__file__).resolve().parents[2] / "content" / "rejections" / "pending"


def write_pending(
    text: str,
    reason: RejectionReason | str,
    language: str,
    *,
    item_id: str,
    note: str = "",
    directory: Path | None = None,
    date: str | None = None,
) -> Path:
    """Save one rejection as the next numbered file for that date. The excerpt is reviewed content
    (a draft the coach rejected), never teacher text."""
    folder = directory or PENDING_DIR
    folder.mkdir(parents=True, exist_ok=True)
    day = date or datetime.now(UTC).date().isoformat()
    n = len(list(folder.glob(f"{day}-*.yaml"))) + 1
    path = folder / f"{day}-{n:03d}.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "reason": RejectionReason(reason).value,
                "language": language,
                "text": text,
                "item_id": item_id,
                "note": note[:300],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def list_pending(directory: Path | None = None) -> list[Path]:
    folder = directory or PENDING_DIR
    return sorted(folder.glob("*.yaml")) if folder.exists() else []
