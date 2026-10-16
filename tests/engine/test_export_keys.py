import hashlib
import json
from pathlib import Path

from engine.diagnosis import MIN_CHILDREN_CHECKED, MIN_HITS
from engine.export_keys import build_answer_keys, build_diagnosis_cases, render
from engine.forms import PILOT_FORMS

ROOT = Path(__file__).resolve().parents[2]
KEYS_PATH = ROOT / "apps/pwa/src/generated/answer_keys.json"
CASES_PATH = ROOT / "tests/fixtures/diagnosis_cases.json"


def test_keys_cover_both_pilot_forms_with_ten_items() -> None:
    keys = build_answer_keys(PILOT_FORMS)
    assert set(keys["forms"]) == {"A", "B"}
    assert all(len(f["items"]) == 10 for f in keys["forms"].values())


def test_keys_carry_the_scoring_rules() -> None:
    rules = build_answer_keys(PILOT_FORMS)["rules"]
    assert rules["min_hits"] == MIN_HITS
    assert rules["min_children_checked"] == MIN_CHILDREN_CHECKED
    assert rules["min_prevalence"] == {"numerator": 1, "denominator": 4}
    assert "PV-REVERSE" not in rules["tracked"]


def test_item_one_maps_wrong_answers_to_codes() -> None:
    item = build_answer_keys(PILOT_FORMS)["forms"]["A"]["items"][0]
    assert item["correct"] == 346
    assert item["wrong"]["30046"] == ["PV-HEARD"]
    assert item["wrong"]["364"] == ["PV-REVERSE"]
    assert item["wrong"]["30064"] == ["PV-HEARD", "PV-REVERSE"]
    assert item["probes"] == ["PV-HEARD", "PV-REVERSE"]


def test_untracked_signature_is_exported() -> None:
    item = build_answer_keys(PILOT_FORMS)["forms"]["A"]["items"][2]
    assert item["untracked"] == {"715": "ADD-WHOLE-ONES"}


def test_content_hash_covers_everything_else() -> None:
    keys = build_answer_keys(PILOT_FORMS)
    body = {k: v for k, v in keys.items() if k != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert keys["content_hash"] == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_build_is_deterministic() -> None:
    assert build_answer_keys(PILOT_FORMS) == build_answer_keys(PILOT_FORMS)
    assert build_diagnosis_cases() == build_diagnosis_cases()


def test_cases_include_the_hard_ones() -> None:
    cases = build_diagnosis_cases()
    names = {c["name"] for c in cases["children"]}
    assert {
        "devanagari_correct",
        "heard_and_reversed_both",
        "715_untracked",
        "anchor_wrong",
    } <= names
    assert len(cases["children"]) >= 100 and len(cases["classes"]) >= 8
    devanagari = next(c for c in cases["children"] if c["name"] == "devanagari_correct")
    assert devanagari["expected"]["shows"] == [] and devanagari["raw"][0] == "३४६"


def test_committed_files_are_not_stale() -> None:
    """Fails if engine code changed without re-running `python tasks.py export-keys`."""
    assert KEYS_PATH.read_text(encoding="utf-8") == render(build_answer_keys(PILOT_FORMS))
    assert CASES_PATH.read_text(encoding="utf-8") == render(build_diagnosis_cases())
