"""AI_USAGE.md cannot drift from the repo: calls, file paths and the Verified claims are checked."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.registry import CALLS  # noqa: E402
from scripts.gen_ai_usage import FALLBACKS, build  # noqa: E402

DOC = ROOT / "AI_USAGE.md"
PROOF = ROOT / "docs" / "evidence" / "ai_usage_proof.json"
STATUSES = {"Specified", "Built", "Verified"}


def text() -> str:
    return DOC.read_text(encoding="utf-8")


def capability_rows() -> list[list[str]]:
    sec = text().split("## 3. Capability map", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in sec.splitlines() if r.startswith("|") and not r.startswith("| ---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def test_every_call_in_the_registry_is_in_the_doc_with_a_fallback() -> None:
    section = text().split("<!-- REGISTRY:START -->", 1)[1].split("<!-- REGISTRY:END -->", 1)[0]
    for call in CALLS:
        assert re.search(rf"^\| {call.id} \|", section, re.M), call.id
        assert call.id in FALLBACKS, f"call {call.id} has no fallback in scripts/gen_ai_usage.py"


def test_the_registry_section_is_current() -> None:
    assert build(text()) == text(), "run: python scripts/gen_ai_usage.py"


def test_every_file_path_in_the_doc_exists() -> None:
    generated = {"docs/evidence/ai_usage_proof.json"}  # written by scripts/ai_proof.py
    missing = []
    for token in re.findall(r"`([^`\n]+)`", text()):
        path = token.split("#", 1)[0].strip()
        if (
            "/" not in path
            or " " in path
            or path.startswith(("http", "GET", "POST", "python"))
            or any(ch in path for ch in "<>*{}")
        ):
            continue
        if path in generated:
            continue
        if not (ROOT / path).exists():
            missing.append(path)
    assert not missing, missing


def test_statuses_are_one_of_three_words() -> None:
    rows = capability_rows()
    assert len(rows) >= 15
    assert {r[4] for r in rows} <= STATUSES


def test_a_verified_row_needs_a_pass_in_the_proof_file() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8")) if PROOF.exists() else {"checks": {}}
    for row in capability_rows():
        if row[4] != "Verified":
            continue
        keys = re.findall(r"ai_usage_proof\.json#(\w+)", row[5])
        assert keys, f"{row[0]} is Verified but names no proof key"
        for key in keys:
            status = proof.get("checks", {}).get(key, {}).get("status")
            assert status == "PASS", f"{row[0]} is Verified but {key} is {status}"


def test_a_built_row_names_a_file_and_a_specified_row_is_not_dressed_as_built() -> None:
    for row in capability_rows():
        if row[4] == "Built":
            assert re.search(r"`[^`]+/[^`]+`|`[^`]+\.\w+`", row[3]), row[0]
        if row[4] == "Specified":
            assert "Built" not in row[3] and "Verified" not in row[3], row[0]
