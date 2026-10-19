"""Guards for the kit v3 migration (docs/build/reports/MIGRATION-v1-v3.md)."""

from __future__ import annotations

import re
from pathlib import Path

from ai.config import DEFAULT_MODELS

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_claude_md_is_v3_with_rules_11_to_14() -> None:
    text = read("CLAUDE.md")
    rules = (
        "11. **Adoption honesty.**",
        "12. **Time caps.**",
        "13. **Simulated practice is a hypothesis.**",
        "14. **One back end, thin channels.**",
    )
    for rule in rules:
        assert rule in text
    assert "evidence-digest.md" in text and "No finguru voice server" in text  # build edit kept


def test_simulated_practice_is_called_a_hypothesis_in_readme_and_practice_docs() -> None:
    for rel in ("README.md", "docs/practice-class.md"):
        text = read(rel).lower()
        assert "hypothesis" in text and "pilot" in text, rel
        assert not re.search(r"practice (is|was|has been) (proven|shown|effective)", text), rel
        assert "proven effective" not in text, rel


def test_no_doc_says_a_voice_note_was_listened_to_or_watched() -> None:
    bad = re.compile(
        r"\b(listened|watched|listens|listening)\s+(to\s+)?(a |the |each |every )?"
        r"(voice|lesson|audio|video)",
        re.I,
    )
    for path in (ROOT / "docs").rglob("*.md"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("docs/design/", "docs/build/")):
            continue
        assert not bad.search(path.read_text(encoding="utf-8")), rel
    assert not bad.search(read("README.md"))


def test_env_example_lists_every_model_variable_including_call_9() -> None:
    env = read(".env.example")
    keys = set(re.findall(r"^([A-Z0-9_]+)=", env, re.M))
    assert set(DEFAULT_MODELS) <= keys
    assert DEFAULT_MODELS.get("MODEL_POINTER") == "claude-haiku-5-5"
    assert "TELEGRAM_BOT_TOKEN" in keys


def test_decisions_are_newest_first_and_record_the_v3_migration() -> None:
    text = read("docs/build/DECISIONS.md")
    settled = text.split("## Settled decisions", 1)[1]
    dates = re.findall(r"^### (\d{4}-\d{2}-\d{2}) ·", settled, re.M)
    assert dates == sorted(dates, reverse=True)
    assert "Kit v3 adopted" in settled and "P07 live check" in settled


def test_docs_that_describe_the_v1_phone_check_point_to_the_v3_plan() -> None:
    for rel in ("docs/offline.md", "docs/architecture.md"):
        assert "kit v3" in read(rel).lower(), rel
