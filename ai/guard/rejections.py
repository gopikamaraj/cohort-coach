"""Structured rejection reasons and the approved examples that feed call 7."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml

APPROVED_DIR = Path(__file__).resolve().parents[2] / "content" / "rejections" / "approved"


class RejectionReason(StrEnum):
    WRONG_MATHS = "wrong_maths"
    CULTURALLY_OFF = "culturally_off"
    TOO_COMPLEX_FOR_MEDIUM = "too_complex_for_medium"
    TONE_ISSUE = "tone_issue"
    FACTUALLY_SHAKY = "factually_shaky"


def add_approved_example(
    text: str, reason: RejectionReason, language: str, *, date: str, directory: Path | None = None
) -> Path:
    """Save one reviewed rejection as the next numbered file for that date."""
    folder = directory or APPROVED_DIR
    folder.mkdir(parents=True, exist_ok=True)
    n = len(list(folder.glob(f"{date}-*.yaml"))) + 1
    path = folder / f"{date}-{n:03d}.yaml"
    path.write_text(
        yaml.safe_dump(
            {"reason": RejectionReason(reason).value, "language": language, "text": text},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def latest_examples(n: int = 5, directory: Path | None = None) -> list[dict[str, str]]:
    """The latest n approved examples, newest last."""
    folder = directory or APPROVED_DIR
    files = sorted(folder.glob("*.yaml"))[-n:] if folder.exists() else []
    out: list[dict[str, str]] = []
    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        RejectionReason(data["reason"])  # a bad reason is a bad file: fail loudly
        out.append({k: str(data[k]) for k in ("reason", "language", "text")})
    return out


def examples_block(n: int = 5, directory: Path | None = None) -> str:
    """The 'rejected before, and why' text appended to call 7's prompt. Empty when none."""
    examples = latest_examples(n, directory)
    if not examples:
        return ""
    lines = ["Rejected before, and why (fail text that makes the same mistake):"]
    lines += [f'- [{e["reason"]}, {e["language"]}] "{e["text"]}"' for e in examples]
    return "\n".join(lines)
