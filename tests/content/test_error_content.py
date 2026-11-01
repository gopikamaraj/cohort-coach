"""The error explanations and the intervention pack text (autopilot Parts C and E).

Every error the engine can show a teacher has an explanation; the file the phone reads matches the
content files; the pack never leaves a strategy without steps, and never holds a Form A or Form B
item (the content scan in test_track_content.py also covers content/errors).
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.bugs import answer_codes, correct_answer
from engine.export_keys import build_answer_keys
from engine.forms import PILOT_FORMS
from engine.model import ErrorCode
from services.content import error_content as ec

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "apps" / "pwa" / "src" / "generated" / "error_content.json"
ENGINE_CODES = [c.value for c in ErrorCode]


def test_every_error_code_the_engine_can_produce_has_a_complete_explanation() -> None:
    have = ec.explanations()["errors"]
    for code in [*ENGINE_CODES, ec.UNTRACKED]:
        assert code in have, f"no explanation for {code}"
        for field in ec.EXPLANATION_FIELDS:
            text = have[code][field]["en"]
            assert isinstance(text, str) and len(text) > 20, (code, field)


def test_every_error_has_a_plain_name_in_all_three_languages() -> None:
    names = ec.names()
    for code in ENGINE_CODES:
        assert set(names[code]) >= {"en", "hi", "ta"}, code


def test_every_error_has_all_the_pack_sections_or_the_pack_leaves_it_out() -> None:
    pack = ec.intervention()["errors"]
    for code in ENGINE_CODES:
        assert code in pack, f"no intervention text for {code}"
        for field in ec.PACK_FIELDS:
            assert pack[code][field]["en"], (code, field)


def test_every_strategy_the_pack_can_show_has_steps_and_materials() -> None:
    iv = ec.intervention()
    for sid in ec.strategies()["strategies"]:
        detail = iv["strategy_details"][sid]
        assert detail["steps"]["en"] and detail["materials"]["en"], sid
    for extras in iv["extra_strategies"].values():
        for s in extras:
            assert s["steps"]["en"] and s["materials"]["en"] and s["description"]["en"], s["id"]


def test_the_library_plus_the_extras_cover_every_error_with_a_strategy() -> None:
    fits: dict[str, int] = {c: 0 for c in ENGINE_CODES}
    for s in ec.strategies()["strategies"].values():
        for code in s["fits"]:
            fits[code] = fits.get(code, 0) + 1
    extras = ec.intervention()["extra_strategies"]
    for code in ENGINE_CODES:
        assert fits[code] + len(extras.get(code, [])) >= 1, f"no strategy at all for {code}"


def test_the_file_the_phone_reads_is_what_the_content_files_say() -> None:
    assert json.loads(GENERATED.read_text(encoding="utf-8")) == json.loads(
        json.dumps(ec.build(), ensure_ascii=False)
    ), "run python tasks.py export-keys"


def test_the_worked_example_is_the_bug_functions_answer_on_the_classs_own_question() -> None:
    """The phone fills "writes W for the question; the correct answer is C" from the answer key.
    Prove the key's wrong answers and their codes are exactly the engine's, on every item."""
    keys = build_answer_keys(PILOT_FORMS)
    for name, form in PILOT_FORMS.items():
        for item, key in zip(form.items, keys["forms"][name]["items"], strict=True):
            from_key = {int(a): set(codes) for a, codes in key["wrong"].items()}
            from_engine = {a: {c.value for c in cs} for a, cs in answer_codes(item).items()}
            assert from_key == from_engine, (name, item.n)
            assert key["correct"] == correct_answer(item)
