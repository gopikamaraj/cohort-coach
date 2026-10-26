"""Rejections waiting to become checker examples.

A coach's rejection writes the excerpt and the structured reason to `content/rejections/pending/`.
Nothing there reaches call 7. Someone curates it: "use as checker example" promotes a file to
`approved/` (`promote`), which is what ai/guard/rejections.py reads into call 7's prompt. This
keeps one careless click from teaching the checker the wrong lesson.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai.guard.rejections import RejectionReason, add_approved_example

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


_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")


def find_pending(name: str, directory: Path | None = None) -> Path:
    """A pending file by its name (no extension). The name must look like one of ours, so a
    request cannot reach any other file."""
    if not _NAME.match(name):
        raise ValueError("That is not the name of a pending example.")
    path = (directory or PENDING_DIR) / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(name)
    return path


def promote(path: Path, *, text: str | None = None) -> Path:
    """ "Use as checker example": move a pending rejection to approved/, where call 7 reads it.
    The curator may trim the excerpt to the sentence that was wrong. A file whose reason is not on
    the list is refused and stays where it is."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    reason = RejectionReason(data["reason"])  # ValueError if it is not one of the five
    excerpt = (text if text is not None else str(data["text"])).strip()
    if not excerpt:
        raise ValueError("An example needs some text.")
    saved = add_approved_example(
        excerpt, reason, str(data["language"]), date=datetime.now(UTC).date().isoformat()
    )
    path.unlink()
    return saved


def discard(path: Path) -> None:
    path.unlink()
