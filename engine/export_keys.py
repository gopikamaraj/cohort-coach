"""Builds the answer keys the PWA diagnoses with, and the golden cases that prove parity.

Pure functions: scripts/export_keys.py does the file writing. The TypeScript side does lookups
only; every wrong answer and rule below is computed here, in Python.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from engine.bugs import (
    answer_codes,
    correct_answer,
    probes,
    untracked_signatures,
)
from engine.diagnosis import (
    MIN_CHILDREN_CHECKED,
    MIN_HITS,
    MIN_PREVALENCE_DENOMINATOR,
    MIN_PREVALENCE_NUMERATOR,
    TRACKED,
    class_profile,
    diagnose_child,
)
from engine.forms import PILOT_FORMS
from engine.model import ChildDiagnosis, ClassProfile, ErrorCode, Form, Reading
from engine.normalize import normalize_answer

KEYS_VERSION = 1
CASES_SEED = 2026


def render(data: dict[str, Any]) -> str:
    """Canonical text of a generated JSON file (stable bytes, so drift is detectable)."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _item_key(form: Form, index: int) -> dict[str, Any]:
    item = form.items[index]
    wrong = {str(ans): sorted(c.value for c in cs) for ans, cs in answer_codes(item).items()}
    untracked = {
        str(ans): name for name, answers in untracked_signatures(item).items() for ans in answers
    }
    return {
        "n": item.n,
        "type": item.type.value,
        "correct": correct_answer(item),
        "probes": [c.value for c in probes(item)],
        "wrong": wrong,
        "untracked": untracked,
    }


def build_answer_keys(forms: dict[str, Form] = PILOT_FORMS) -> dict[str, Any]:
    body: dict[str, Any] = {
        "version": KEYS_VERSION,
        "error_order": [c.value for c in ErrorCode],
        "rules": {
            "min_hits": MIN_HITS,
            "min_prevalence": {
                "numerator": MIN_PREVALENCE_NUMERATOR,
                "denominator": MIN_PREVALENCE_DENOMINATOR,
            },
            "min_children_checked": MIN_CHILDREN_CHECKED,
            "tracked": [c.value for c in TRACKED],
            "track_priority": "PV-HEARD first, else highest count; ties by error order",
        },
        "forms": {
            key: {
                "label": form.label,
                "items": [_item_key(form, i) for i in range(len(form.items))],
            }
            for key, form in forms.items()
        },
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return body


# --- golden diagnosis cases ---------------------------------------------------------------


def _expected_child(d: ChildDiagnosis) -> dict[str, Any]:
    return {
        "marks": [
            {
                "kind": m.kind.value,
                "codes": sorted(c.value for c in m.codes),
                "untracked": m.untracked,
            }
            for m in d.marks
        ],
        "shows": sorted(c.value for c in d.shows),
        "anchor_wrong": d.anchor_wrong,
        "other_count": d.other_count,
        "blank_count": d.blank_count,
        "unreadable_count": d.unreadable_count,
        "untracked": dict(sorted(d.untracked.items())),
    }


def _expected_class(p: ClassProfile) -> dict[str, Any]:
    return {
        "children_checked": p.children_checked,
        "counts": {c.value: n for c, n in p.counts.items()},
        "prevalence": {c.value: v for c, v in p.prevalence.items()},
        "eligible": [c.value for c in p.eligible],
        "track": p.track.value if p.track else None,
        "anchor_wrong_count": p.anchor_wrong_count,
        "untracked": dict(sorted(p.untracked.items())),
    }


def _readings(raw: list[str]) -> list[Reading]:
    return [normalize_answer(x) for x in raw]


# Form A correct answers: 346 728 85 74 82 35 38 26 43 54
_A_CORRECT = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"]


def _named(over: dict[int, str]) -> list[str]:
    out = list(_A_CORRECT)
    for n, text in over.items():
        out[n - 1] = text
    return out


_NAMED: list[tuple[str, list[str]]] = [
    ("all_correct", _A_CORRECT),
    ("devanagari_correct", ["३४६", "७२८", "८५", "७४", "८२", "३५", "३८", "२६", "४३", "५४"]),
    ("tamil_digits_error", _named({3: "௭௫", 4: "௬௪"})),
    ("one_hit_not_shown", _named({3: "75"})),
    ("nocarry_two_hits", _named({3: "75", 5: "72"})),
    ("heard_both_items", _named({1: "30046", 2: "70028"})),
    ("reverse_both_items", _named({1: "364", 2: "782"})),
    ("heard_and_reversed_both", _named({1: "30064", 2: "70082"})),
    ("sfl_two_hits", _named({7: "42", 10: "66"})),
    ("nodec_two_hits", _named({8: "36", 9: "53"})),
    ("anchor_wrong", _named({6: "25", 7: "42", 8: "34"})),
    ("715_untracked", _named({3: "715", 4: "614"})),
    ("blanks_and_junk", _named({3: "", 4: "abc", 5: "?", 7: "  "})),
    ("blank_does_not_complete_a_pair", _named({3: "75", 4: "", 5: ""})),
]


def _random_child(rng: random.Random) -> list[str]:
    """One child's raw answers on Form A: each box correct, a known error, junk or blank."""
    form = PILOT_FORMS["A"]
    out: list[str] = []
    for item in form.items:
        roll = rng.random()
        wrong = sorted(answer_codes(item))
        if roll < 0.45 or not wrong:
            out.append(str(correct_answer(item)))
        elif roll < 0.85:
            out.append(str(rng.choice(wrong)))
        elif roll < 0.92:
            out.append(str(rng.randint(1, 999)))
        elif roll < 0.96:
            out.append("")
        else:
            out.append(rng.choice(["?", "x", "3 4", "३४"]))
    return out


def build_diagnosis_cases() -> dict[str, Any]:
    form = PILOT_FORMS["A"]
    rng = random.Random(CASES_SEED)
    children: list[dict[str, Any]] = []
    for name, raw in _NAMED:
        children.append({"name": name, "form": "A", "raw": raw})
    for i in range(120):
        children.append({"name": f"random_{i:03d}", "form": "A", "raw": _random_child(rng)})
    for c in children:
        c["expected"] = _expected_child(diagnose_child(form, _readings(c["raw"])))

    sizes = [0, 5, 9, 10, 12, 16, 20, 30]
    classes: list[dict[str, Any]] = []
    for size in sizes:
        raws = [_random_child(rng) for _ in range(size)]
        profile = class_profile([diagnose_child(form, _readings(r)) for r in raws])
        classes.append(
            {
                "name": f"class_of_{size}",
                "form": "A",
                "children": raws,
                "expected": _expected_class(profile),
            }
        )
    return {
        "_about": "Synthetic answer vectors (seed 2026), generated by engine/export_keys.py. "
        "No real child. Do not edit by hand; run `python tasks.py export-keys`.",
        "seed": CASES_SEED,
        "children": children,
        "classes": classes,
    }
