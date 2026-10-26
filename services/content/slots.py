"""Class-number slots: the only way a number about a class may appear in track content.

A slot is written `{{name}}` in a template or draft and filled by code at delivery time, per
cohort (CLAUDE.md rule 1: code computes every number; the model never states one). The list is
closed: a draft that names any other slot is refused.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from ai.validators import Violation
from ai.validators._data import ascii_digits
from engine.bugs import add_nocarry, pv_heard, sub_nodec, sub_sfl

# slot name -> where its value comes from (shown in the review queue so a reviewer sees it is code)
SLOT_SOURCES: dict[str, str] = {
    "class.count_showing": "engine: children who show this error (2-item rule)",
    "class.children_checked": "engine: children checked",
    "class.example_a": "engine: first number of the worked example for this error",
    "class.example_b": "engine: second number of the worked example (none for dictation errors)",
    "class.example_wrong_answer": "engine: the error function's wrong answer for the example",
    "class.example_correct_answer": "engine: the correct answer for the example",
    "track.error_name": "content/lang/error_names.yaml, in the teacher's language",
    "track.day": "the lesson's day in the track",
    "track.total_days": "the number of lessons in the track",
}
SLOT_NAMES: tuple[str, ...] = tuple(SLOT_SOURCES)


_SLOT = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
WRONG_TAG = " [child-wrong]"


class SlotError(ValueError):
    """A slot problem: the draft names a slot that does not exist, or no value was given."""


class UnknownSlot(SlotError):
    pass


class UnfilledSlot(SlotError):
    pass


def slots_used(text: str) -> list[str]:
    return _SLOT.findall(text)


def check_slots(text: str) -> list[Violation]:
    """Gate 1: a draft may name only the slots on the closed list."""
    return [
        Violation("slot_unknown", f"{{{{{name}}}}} is not a slot")
        for name in dict.fromkeys(slots_used(text))
        if name not in SLOT_SOURCES
    ]


def fill(text: str, values: Mapping[str, str], *, keep_tags: bool = False) -> str:
    """Fill every slot by code. The wrong-answer slot carries the child-wrong tag while the text is
    being checked (keep_tags=True); the text that is shown or voiced has it stripped."""

    def one(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in SLOT_SOURCES:
            raise UnknownSlot(name)
        if name not in values:
            raise UnfilledSlot(name)
        value = str(values[name])
        if name == "class.example_wrong_answer" and keep_tags:
            return value + WRONG_TAG
        return value

    return _SLOT.sub(one, text)


def example_values(error: str, a: int, b: int | None = None) -> dict[str, str]:
    """The worked-example slots for an error, computed by the engine (never the model)."""
    if error == "PV-HEARD":
        correct, wrong, second = a, min(pv_heard(a)), None
    elif b is None:
        raise ValueError(f"{error} needs two numbers")
    elif error == "ADD-NOCARRY":
        correct, wrong, second = a + b, min(add_nocarry(a, b)), b
    elif error == "SUB-SFL":
        correct, wrong, second = a - b, min(sub_sfl(a, b)), b
    elif error == "SUB-NODEC":
        correct, wrong, second = a - b, min(sub_nodec(a, b)), b
    else:
        raise ValueError(f"no worked example for {error}")
    out = {
        "class.example_a": str(a),
        "class.example_correct_answer": str(correct),
        "class.example_wrong_answer": str(wrong),
    }
    if second is not None:
        out["class.example_b"] = str(second)
    return out


# A literal count of children or a percentage written into text. Worked examples (sums, sticks)
# are not class numbers; a slot (still in braces) is not a literal.
_CHILD_WORDS = (
    r"children|child|kids|pupils|students|बच्चों|बच्चे|बच्चा|विद्यार्थी|"
    r"குழந்தைகள்|குழந்தை|மாணவர்கள்"
)
_DID = (
    r"made|make|showed|show|shows|have|has|had|got|get|wrote|write|writes|do|did|"
    r"struggle|struggled|face|faced|need|needed|found|find"
)
_COUNT_PATTERNS = (
    re.compile(rf"\b\d+\s*(?:of|out of)\s*\d+\s*(?:{_CHILD_WORDS})", re.I),
    re.compile(rf"\bout of\s*\d+\s*(?:{_CHILD_WORDS})", re.I),
    # "11 children made the mistake" is a class count; "try it with 3 children" is an instruction
    re.compile(rf"(?<![\w{{])\d+\s*(?:children|kids|pupils|students)\s+(?:{_DID})\b", re.I),
    re.compile(r"(?<![\w{])\d+\s*बच्चों\s*ने"),
    re.compile(r"(?<![\w{])\d+\s*(?:குழந்தைகள்|மாணவர்கள்)\s*(?:இந்த|தவறு|செய்)"),
    re.compile(r"\d+(?:\.\d+)?\s*%"),
    re.compile(r"\bpercent(?:age)?\b|प्रतिशत|சதவீதம்", re.I),
)


def literal_class_counts(text: str) -> list[Violation]:
    """Gate 1 for rule 1: no real count of children and no percentage in teacher-facing text; those
    numbers come only through slots. Limits: it catches counts written next to a word for children
    and any percentage; the arithmetic and check-item validators cover the rest."""
    plain = ascii_digits(_SLOT.sub("", text))
    hits: list[Violation] = []
    for pattern in _COUNT_PATTERNS:
        for m in pattern.finditer(plain):
            hits.append(Violation("class_number_literal", m.group().strip()))
    return hits


# Stand-in values used only to check how a draft reads once its slots are filled. They are never
# shown to a teacher: delivery fills real values per cohort (fill()).
SAMPLE_VALUES: dict[str, str] = {
    "class.count_showing": "11",
    "class.children_checked": "28",
    "class.example_a": "52",
    "class.example_b": "29",
    "class.example_wrong_answer": "37 [child-wrong]",
    "class.example_correct_answer": "23",
    "track.error_name": "taking the smaller digit from the larger",
    "track.day": "2",
    "track.total_days": "6",
}


def sample_fill(text: str) -> str:
    """Fill known slots with sample values; an unknown slot is left in place for check_slots."""
    return _SLOT.sub(lambda m: SAMPLE_VALUES.get(m.group(1), m.group(0)), text)
