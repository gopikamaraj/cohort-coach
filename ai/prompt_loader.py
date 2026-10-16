"""Load versioned prompt files from ai/prompts/ (front matter: id, version, model, changelog)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

PROMPT_DIR = Path(__file__).with_name("prompts")


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    model_env: str
    changelog: tuple[str, ...]
    body: str  # the stable system text; it goes first so it can be cached


@cache
def load_prompt(prompt_id: str, version: int | None = None) -> Prompt:
    """The highest version of this prompt unless a version is asked for."""
    if version is None:
        files = sorted(PROMPT_DIR.glob(f"{prompt_id}.v*.md"))
        if not files:
            raise FileNotFoundError(f"no prompt file for {prompt_id}")
        path = files[-1]
    else:
        path = PROMPT_DIR / f"{prompt_id}.v{version}.md"
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path.name} has no front matter")
    head, _, body = raw[4:].partition("\n---\n")
    meta = yaml.safe_load(head)
    for key in ("id", "version", "model", "changelog"):
        if key not in meta:
            raise ValueError(f"{path.name} front matter is missing {key}")
    if meta["id"] != prompt_id:
        raise ValueError(f"{path.name} says id {meta['id']}")
    return Prompt(
        id=meta["id"],
        version=int(meta["version"]),
        model_env=meta["model"],
        changelog=tuple(str(c) for c in meta["changelog"]),
        body=body.strip(),
    )
