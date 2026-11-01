"""A call is marked built only when code calls it, so no screen or README shows a planned call as
working (QA-DEMO H3)."""

from __future__ import annotations

import re
from pathlib import Path

from ai.registry import CALLS

ROOT = Path(__file__).resolve().parents[2]
CODE = [
    p
    for d in ("ai", "services", "scripts", "tools")
    for p in (ROOT / d).rglob("*.py")
    if p.name not in {"registry.py", "config.py"}
]
TEXT = "\n".join(p.read_text(encoding="utf-8") for p in CODE)


def called(call_id: int, key: str) -> bool:
    """A call module in ai/calls/ (each one calls run_call), or a direct run_call elsewhere."""
    module = ROOT / "ai" / "calls" / f"{key}.py"
    return module.exists() or bool(re.search(rf"run_call\(\s*(?:{call_id}\s*,|\"{key}\")", TEXT))


def test_built_means_some_code_calls_it() -> None:
    for c in CALLS:
        assert c.built == called(c.id, c.key), (c.id, c.key, c.built)


def test_calls_4_and_6_are_planned() -> None:
    assert {c.id for c in CALLS if not c.built} == {4, 6}
