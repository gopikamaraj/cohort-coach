"""Rule 14: a channel adapter and the web app only render and return answers. They import nothing
from `engine/` or `ai/`, so they cannot compute a number or call a model."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNED = re.compile(r"^\s*(from|import)\s+(engine|ai)(\.|\s|$)", re.M)


def test_channels_import_nothing_from_engine_or_ai() -> None:
    files = list((ROOT / "services/api/channels").rglob("*.py"))
    assert len(files) >= 4
    bad = [str(f.relative_to(ROOT)) for f in files if BANNED.search(f.read_text(encoding="utf-8"))]
    assert not bad, bad


def test_the_web_app_imports_nothing_from_engine_or_ai() -> None:
    src = ROOT / "apps/pwa/src"
    pat = re.compile(r"from ['\"](?:\.\./)+(?:engine|ai)/")
    bad = [
        str(f.relative_to(ROOT))
        for f in list(src.rglob("*.ts")) + list(src.rglob("*.tsx"))
        if pat.search(f.read_text(encoding="utf-8"))
    ]
    assert not bad, bad
