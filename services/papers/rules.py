"""The rule set a paper is built from: templates, bug functions, blueprints and string packs.

A rule set is plain data. Version 1 is seeded from the engine (the error functions in
engine/bugs.py, the check layout in engine/items.py) and the pilot test pack
(docs/design/pilot-test-pack.md: the item difficulties of Form A and the Hindi classroom wording).
A rule set never changes in place: services/papers/store.py keeps each version, and a change is a
new version that a second person approves.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

Competency = Literal["C1", "C2", "C3"]
Operation = Literal["dictate", "add", "subtract"]
LANGS = ("en", "hi", "ta")
# A paper is in one language, or in two (each line in the first, then the second): any pair.
LAYOUTS = (
    "en", "hi", "ta",
    "en_hi", "en_ta", "hi_en", "hi_ta", "ta_en", "ta_hi",
)  # fmt: skip


def layout_langs(layout: str) -> tuple[str, ...]:
    """The languages of a layout, first language first ("hi_ta" -> ("hi", "ta"))."""
    if layout not in LAYOUTS:
        raise ValueError(f"no layout {layout}")
    return tuple(layout.split("_"))


COMPETENCY_NAMES = {
    "C1": "Place value",
    "C2": "Adding with carrying",
    "C3": "Taking away with borrowing",
}


class Template(BaseModel):
    """One kind of item. `constraints` are the digit rules the generator must satisfy."""

    id: str
    competency: Competency
    skill: str
    operation: Operation
    digit_pattern: str
    number_range: tuple[int, int]
    answer_format: str
    # digits: 2 or 3 (dictation) | carry / borrow: "required" or "forbidden" | ones_total: n
    # first_ones: n | gap_not: [n] | sum_max | result_min | tens_gap_min | nonzero | tens_ne_ones
    constraints: dict[str, Any] = Field(default_factory=dict)
    bugs: list[str]  # bug ids from Bug.id that apply to this item
    difficulty: Literal["ones_total", "ones_gap", "none"] = "none"
    retired: bool = False


class Bug(BaseModel):
    """A bug function: the wrong answer a child with this error would write.

    `fn` names a function in engine/bugs.py. `counts_for` lists the error codes an answer counts
    for (the heard-and-reversed answer counts for both place-value errors). `tracked: false` means
    the pattern is tallied, never flagged, and never needs coverage."""

    id: str
    fn: str
    counts_for: list[str]
    tracked: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class Slot(BaseModel):
    n: int
    section: Literal["dictation", "add", "subtract"]
    kind: Literal["anchor", "adaptive"]
    template: str | None = None  # anchors: a fixed template
    difficulty: int | None = None  # anchors: the fixed ones total or ones gap


class Blueprint(BaseModel):
    id: str
    title: str
    slots: list[Slot]
    adaptive_count: int = 0
    adaptive_templates: dict[Competency, list[str]] = Field(default_factory=dict)
    coverage_min: int = 2
    coverage_codes: list[str]
    # Pairs of error codes that are allowed to share a wrong answer on purpose.
    intended_overlaps: list[tuple[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _slots(self) -> Blueprint:
        ns = [s.n for s in self.slots]
        if ns != list(range(1, len(ns) + 1)):
            raise ValueError(f"blueprint {self.id}: slots must be numbered 1..{len(ns)}")
        for s in self.slots:
            if s.kind == "anchor" and not s.template:
                raise ValueError(f"blueprint {self.id}: anchor slot {s.n} needs a template")
        return self


class StringPack(BaseModel):
    """Fixed paper wording in one language, written and reviewed by people.

    `source` says where the words came from; `reviewed_by` is empty until a person who reads the
    language has checked them. A paper in an unreviewed language is never auto-approved."""

    lang: str
    strings: dict[str, str]
    source: str
    reviewed_by: str = ""


class RuleSet(BaseModel):
    templates: list[Template]
    bugs: list[Bug]
    blueprints: list[Blueprint]
    string_packs: list[StringPack]

    @model_validator(mode="after")
    def _refs(self) -> RuleSet:
        t_ids = {t.id for t in self.templates}
        b_ids = {b.id for b in self.bugs}
        for t in self.templates:
            missing = set(t.bugs) - b_ids
            if missing:
                raise ValueError(f"template {t.id} names unknown bugs {sorted(missing)}")
        for bp in self.blueprints:
            for s in bp.slots:
                if s.template and s.template not in t_ids:
                    raise ValueError(f"blueprint {bp.id} slot {s.n}: unknown template {s.template}")
            for comp, ids in bp.adaptive_templates.items():
                if set(ids) - t_ids:
                    raise ValueError(f"blueprint {bp.id}: unknown adaptive templates for {comp}")
        langs = {p.lang for p in self.string_packs}
        if set(LANGS) - langs:
            raise ValueError(f"string packs missing for {sorted(set(LANGS) - langs)}")
        keys = {p.lang: set(p.strings) for p in self.string_packs}
        for lang, ks in keys.items():
            if ks != keys["en"]:
                raise ValueError(f"string pack {lang} differs from en: {sorted(ks ^ keys['en'])}")
        return self

    def template(self, tid: str) -> Template:
        return next(t for t in self.templates if t.id == tid)

    def bug(self, bid: str) -> Bug:
        return next(b for b in self.bugs if b.id == bid)

    def blueprint(self, bid: str) -> Blueprint:
        for bp in self.blueprints:
            if bp.id == bid:
                return bp
        raise KeyError(f"no blueprint {bid}")

    def pack(self, lang: str) -> StringPack:
        return next(p for p in self.string_packs if p.lang == lang)


# --- version 1 ------------------------------------------------------------------------------

# Form A's difficulties, item by item (pilot test pack): ones totals 15, 14, 12 on items 3-5 and
# ones gaps 2, 4, 7, 6 on items 7-10. Anchors keep these, so every paper measures the same thing.
_ANCHORS: list[tuple[str, str, int | None]] = [
    ("dictation", "dictate-3d", None),
    ("dictation", "dictate-3d", None),
    ("add", "add-carry", 15),
    ("add", "add-carry", 14),
    ("add", "add-carry", 12),
    ("subtract", "sub-no-borrow", None),
    ("subtract", "sub-borrow", 2),
    ("subtract", "sub-borrow", 4),
    ("subtract", "sub-borrow", 7),
    ("subtract", "sub-borrow", 6),
]

_CODES = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"]

_PACK_SOURCE_HI = (
    "Hindi classroom wording in docs/design/pilot-test-pack.md (team, 16 Oct); short section "
    "labels drafted by Claude Code on 30 Oct for a Hindi reader to check"
)


def _strings() -> list[StringPack]:
    en = {
        "paper.roll": "Roll number",
        "paper.no_name": "Do not write your name.",
        "paper.own_way": "Do each question your own way and write the answer in its box.",
        "paper.skip": "If you can't do one, leave it and do the next.",
        "sec.dictation": "Listen to your teacher and write the number.",
        "sec.add": "Add.",
        "sec.subtract": "Take away.",
        "key.title": "Answer key (for the teacher, not the children)",
        "key.item": "Item",
        "key.question": "Question",
        "key.correct": "Correct",
        "key.wrong": "Common wrong answers",
        "key.say": "Say aloud twice",
        "key.anchor": "Anchor",
        "key.adaptive": "Adaptive",
        "key.not_assessed": "Not assessed on this paper",
    }
    hi = {
        "paper.roll": "रोल नंबर",
        "paper.no_name": "नाम मत लिखना।",
        "paper.own_way": "हर सवाल अपने तरीके से करो और उत्तर उसके डिब्बे में लिखो।",
        "paper.skip": "कोई सवाल न आए तो उसे छोड़कर अगला करो।",
        "sec.dictation": "ध्यान से सुनो और संख्या लिखो।",
        "sec.add": "जोड़ो।",
        "sec.subtract": "घटाओ।",
        "key.title": "उत्तर कुंजी (शिक्षक के लिए, बच्चों के लिए नहीं)",
        "key.item": "सवाल",
        "key.question": "प्रश्न",
        "key.correct": "सही उत्तर",
        "key.wrong": "आम गलत उत्तर",
        "key.say": "दो बार बोलें",
        "key.anchor": "स्थिर",
        "key.adaptive": "अनुकूल",
        "key.not_assessed": "इस पेपर में नहीं जाँचा गया",
    }
    ta = {
        "paper.roll": "வரிசை எண்",
        "paper.no_name": "உன் பெயரை எழுத வேண்டாம்.",
        "paper.own_way": "ஒவ்வொரு கணக்கையும் உன் வழியில் செய்து, விடையை அதன் கட்டத்தில் எழுது.",
        "paper.skip": "ஒரு கணக்கு வரவில்லை என்றால், அதை விட்டுவிட்டு அடுத்ததைச் செய்.",
        "sec.dictation": "ஆசிரியர் சொல்வதைக் கேட்டு எண்ணை எழுது.",
        "sec.add": "கூட்டு.",
        "sec.subtract": "கழி.",
        "key.title": "விடைக் குறிப்பு (ஆசிரியருக்கு மட்டும்)",
        "key.item": "கணக்கு",
        "key.question": "கேள்வி",
        "key.correct": "சரியான விடை",
        "key.wrong": "பொதுவான தவறான விடைகள்",
        "key.say": "இரண்டு முறை சொல்லவும்",
        "key.anchor": "நிலையான",
        "key.adaptive": "தகவமைந்த",
        "key.not_assessed": "இந்தத் தாளில் சோதிக்கப்படவில்லை",
    }
    return [
        StringPack(
            lang="en",
            strings=en,
            source="pilot test pack wording (team, 16 Oct)",
            reviewed_by="pilot pack (team, 16 Oct)",
        ),
        StringPack(lang="hi", strings=hi, source=_PACK_SOURCE_HI),
        StringPack(
            lang="ta",
            strings=ta,
            source="drafted by Claude Code on 30 Oct for a Tamil reader to check",
        ),
    ]


def seed_rules() -> RuleSet:
    templates = [
        Template(
            id="dictate-3d",
            competency="C1",
            skill="Write a 3-digit number said aloud",
            operation="dictate",
            digit_pattern="three non-zero digits; tens and ones differ",
            number_range=(111, 999),
            answer_format="a number, written in one wide box",
            constraints={"digits": 3, "nonzero": True, "tens_ne_ones": True},
            bugs=["pv-heard", "pv-reverse", "pv-heard-reversed"],
        ),
        Template(
            id="dictate-2d",
            competency="C1",
            skill="Write a 2-digit number said aloud",
            operation="dictate",
            digit_pattern="two non-zero digits that differ",
            number_range=(12, 98),
            answer_format="a number, written in one wide box",
            constraints={"digits": 2, "nonzero": True, "tens_ne_ones": True},
            bugs=["pv-heard", "pv-reverse", "pv-heard-reversed"],
        ),
        Template(
            id="add-carry",
            competency="C2",
            skill="Add two 2-digit numbers, with carrying",
            operation="add",
            digit_pattern="ones total 10 or more; sum at most 99",
            number_range=(10, 99),
            answer_format="a number, written in one wide box",
            constraints={"carry": "required", "sum_max": 99},
            bugs=["add-nocarry", "add-whole-ones"],
            difficulty="ones_total",
        ),
        Template(
            id="add-carry-ten",
            competency="C2",
            skill="Add with carrying where the answer ends in zero",
            operation="add",
            digit_pattern="ones total exactly 10; sum at most 99",
            number_range=(10, 99),
            answer_format="a number, written in one wide box",
            constraints={"carry": "required", "ones_total": 10, "sum_max": 99},
            bugs=["add-nocarry", "add-whole-ones"],
        ),
        Template(
            id="sub-no-borrow",
            competency="C3",
            skill="Take away without borrowing (anchor: can the child subtract at all)",
            operation="subtract",
            digit_pattern="each digit of the first number at least the one below it",
            number_range=(10, 99),
            answer_format="a number, written in one wide box",
            constraints={"borrow": "forbidden", "tens_gap_min": 1},
            bugs=[],
        ),
        Template(
            id="sub-borrow",
            competency="C3",
            skill="Take away with borrowing",
            operation="subtract",
            digit_pattern="ones digit on top smaller; ones gap not 5; answer at least 10",
            number_range=(10, 99),
            answer_format="a number, written in one wide box",
            constraints={"borrow": "required", "gap_not": [5], "result_min": 10, "tens_gap_min": 2},
            bugs=["sub-sfl", "sub-nodec"],
            difficulty="ones_gap",
        ),
        Template(
            id="sub-borrow-zero",
            competency="C3",
            skill="Take away with borrowing where the top number ends in zero",
            operation="subtract",
            digit_pattern="top ones digit is zero, borrow needed; ones gap not 5",
            number_range=(10, 99),
            answer_format="a number, written in one wide box",
            constraints={
                "borrow": "required",
                "first_ones": 0,
                "gap_not": [5],
                "result_min": 10,
                "tens_gap_min": 2,
            },
            bugs=["sub-sfl", "sub-nodec"],
            difficulty="ones_gap",
        ),
    ]
    bugs = [
        Bug(id="pv-heard", fn="pv_heard", counts_for=["PV-HEARD"]),
        Bug(id="pv-reverse", fn="pv_reverse", counts_for=["PV-REVERSE"]),
        Bug(
            id="pv-heard-reversed",
            fn="heard_and_reversed",
            counts_for=["PV-HEARD", "PV-REVERSE"],
            tracked=False,
        ),
        Bug(id="add-nocarry", fn="add_nocarry", counts_for=["ADD-NOCARRY"]),
        Bug(id="add-whole-ones", fn="add_whole_ones", counts_for=["ADD-WHOLE-ONES"], tracked=False),
        Bug(id="sub-sfl", fn="sub_sfl", counts_for=["SUB-SFL"]),
        Bug(id="sub-nodec", fn="sub_nodec", counts_for=["SUB-NODEC"]),
    ]
    anchors = [
        Slot(n=i + 1, section=sec, kind="anchor", template=tid, difficulty=d)  # type: ignore[arg-type]
        for i, (sec, tid, d) in enumerate(_ANCHORS)
    ]
    adaptive = {
        "C1": ["dictate-2d", "dictate-3d"],
        "C2": ["add-carry-ten", "add-carry"],
        "C3": ["sub-borrow-zero", "sub-borrow"],
    }
    blueprints = [
        Blueprint(
            id="baseline_10",
            title="Baseline: the pilot's 10 items, all anchors",
            slots=anchors,
            coverage_codes=_CODES,
        ),
        Blueprint(
            id="standard_10_5",
            title="Standard: 10 anchor items and 5 adaptive items",
            slots=anchors
            + [
                Slot(n=11 + i, section="subtract", kind="adaptive")  # section set when chosen
                for i in range(5)
            ],
            adaptive_count=5,
            adaptive_templates=adaptive,  # type: ignore[arg-type]
            coverage_codes=_CODES,
        ),
    ]
    return RuleSet(templates=templates, bugs=bugs, blueprints=blueprints, string_packs=_strings())


# --- YAML, hash and diff ------------------------------------------------------------------


def to_data(rules: RuleSet) -> dict[str, Any]:
    return rules.model_dump(mode="json")


def from_data(data: dict[str, Any]) -> RuleSet:
    """Validate a rule set (from the database or an imported YAML file). Raises on a bad file."""
    return RuleSet.model_validate(data)


def to_yaml(rules: RuleSet) -> str:
    return yaml.safe_dump(to_data(rules), allow_unicode=True, sort_keys=False, width=100)


def from_yaml(text: str) -> RuleSet:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("a rules file is a mapping with templates, bugs, blueprints, string_packs")
    return from_data(data)


def rules_hash(rules: RuleSet) -> str:
    canon = json.dumps(to_data(rules), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def diff(old: RuleSet | None, new: RuleSet) -> list[str]:
    """Plain lines saying what changed, entry by entry ("template sub-borrow: constraints ...")."""
    if old is None:
        return ["first version"]
    out: list[str] = []
    for kind, attr in (
        ("template", "templates"),
        ("bug", "bugs"),
        ("blueprint", "blueprints"),
    ):
        a = {x.id: x.model_dump(mode="json") for x in getattr(old, attr)}
        b = {x.id: x.model_dump(mode="json") for x in getattr(new, attr)}
        for k in sorted(b.keys() - a.keys()):
            out.append(f"{kind} {k}: added")
        for k in sorted(a.keys() - b.keys()):
            out.append(f"{kind} {k}: removed")
        for k in sorted(a.keys() & b.keys()):
            for field in sorted(set(a[k]) | set(b[k])):
                if a[k].get(field) != b[k].get(field):
                    out.append(f"{kind} {k}: {field} {a[k].get(field)!r} -> {b[k].get(field)!r}")
    pa = {p.lang: p for p in old.string_packs}
    for p in new.string_packs:
        q = pa.get(p.lang)
        for key in sorted(p.strings):
            if q is None or q.strings.get(key) != p.strings[key]:
                out.append(f"strings {p.lang} {key}: changed")
        if q is not None and q.reviewed_by != p.reviewed_by:
            out.append(f"strings {p.lang}: reviewed by {p.reviewed_by or 'nobody yet'}")
    return out
