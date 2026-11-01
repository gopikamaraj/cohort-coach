"""Import a paper from what is printed on it. The AI reads; code computes; a person confirms.

`PaperRead` (what the vision call returns) holds only the printed questions: operands, operation,
the prompt text, where the answer box is, and a printed answer if the sheet shows a key. Everything
below is code: the correct answer, the competency, the error probes and expected wrong answers (the
engine's own bug functions), an independent re-computation, the coverage grid, the comparison with
a printed key, the merge of several photos of one paper, and the list of open questions. Nothing
here sees a name or a child's answer: when the sheet carries handwriting, every "printed answer"
is dropped, because it is the child's.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

from ai.schemas import PaperRead, ReadPaperItem
from engine.bugs import correct_answer, error_answers, probes
from engine.model import ErrorCode, Item, ItemType

MAX_OPERAND = 999
MIN_PROBES = 2  # fewer than two items probing an error limits diagnosis
COMPETENCY = {"dictate": "C1", "add": "C2", "subtract": "C3"}
SKILL = {
    "dictate": "Write a dictated number in digits",
    "add": "Add whole numbers",
    "subtract": "Subtract whole numbers",
}
TRACKED = (
    ErrorCode.PV_HEARD,
    ErrorCode.PV_REVERSE,
    ErrorCode.ADD_NOCARRY,
    ErrorCode.SUB_SFL,
    ErrorCode.SUB_NODEC,
)


def engine_item(n: int, operation: str, a: int, b: int) -> Item:
    if operation == "dictate":
        return Item(n, ItemType.DICTATION, a)
    if operation == "add":
        return Item(n, ItemType.ADD_CARRY, a, b)
    kind = ItemType.SUB_BORROW if a % 10 < b % 10 else ItemType.SUB_ANCHOR
    return Item(n, kind, a, b)


def _independent_key(operation: str, a: int, b: int) -> int:
    """The key from plain arithmetic, sharing nothing with the engine's bug module."""
    return a if operation == "dictate" else a + b if operation == "add" else a - b


def unsupported_reason(operation: str, a: int | None, b: int | None) -> str | None:
    if operation not in COMPETENCY:
        return "not_a_supported_type"
    if a is None:
        return "dictated_number_needed" if operation == "dictate" else "operand_missing"
    if not 1 <= a <= MAX_OPERAND:
        return "operand_out_of_range"
    if operation == "dictate":
        return None
    if b is None:
        return "operand_missing"
    if not 0 <= b <= MAX_OPERAND:
        return "operand_out_of_range"
    if operation == "add" and a + b > MAX_OPERAND:
        return "sum_over_999"
    if operation == "subtract" and a < b:
        return "negative_result"
    return None


def compute_item(r: ReadPaperItem, *, drop_printed_answer: bool) -> dict[str, Any]:
    """One item with everything code can say about it."""
    reason = unsupported_reason(r.operation, r.a, r.b)
    out: dict[str, Any] = {
        "n": r.n,
        "operation": r.operation,
        "a": r.a,
        "b": r.b,
        "prompt_text": r.prompt_text[:120],
        "box_pct": list(r.box_pct)[:4],
        "unsure": r.unsure,
        "supported": reason is None,
        "reason": reason,
        "include": reason is None,
        "printed_answer": None if drop_printed_answer else r.printed_answer,
        "correct": None,
        "competency": COMPETENCY.get(r.operation),
        "skill": SKILL.get(r.operation),
        "error_probes": [],
        "wrong": {},
        "key_mismatch": False,
        "findings": [],
    }
    if reason is not None:
        return out
    a, b = int(r.a or 0), int(r.b or 0)
    item = engine_item(r.n, r.operation, a, b)
    key = correct_answer(item)
    out["correct"] = key
    out["error_probes"] = [c.value for c in probes(item)]
    out["wrong"] = {c.value: sorted(v) for c, v in error_answers(item).items()}
    if key != _independent_key(r.operation, a, b):
        out["findings"].append("key_disagrees_with_independent_arithmetic")
    printed = out["printed_answer"]
    if printed is not None and str(printed).strip().isdigit() and int(str(printed)) != key:
        out["key_mismatch"] = True
    return out


def coverage(items: Sequence[dict[str, Any]]) -> dict[str, list[int]]:
    """Error code -> the included items that can show it (a wrong answer exists for it)."""
    grid: dict[str, list[int]] = {c.value: [] for c in TRACKED}
    for it in items:
        if it["include"] and it["supported"]:
            for code, answers in it["wrong"].items():
                if answers:
                    grid[code].append(it["n"])
    return grid


def coverage_warnings(grid: dict[str, list[int]]) -> list[str]:
    return [code for code, ns in grid.items() if len(ns) < MIN_PROBES]


def merge(
    reads: Sequence[PaperRead],
    guide: Sequence[PaperRead] = (),
    key: dict[int, int] | None = None,
) -> dict[str, Any]:
    """One draft from one or more reads of the same paper: items by number, a disagreement flagged.

    The operands that most reads give win; any item whose reads differ is marked unsure. The
    handwriting flag is true if any sheet had handwriting, and then no printed answer is kept."""
    handwritten = any(r.contains_handwritten_answers for r in reads)
    # A teacher's guide never adds a question: it only supplies the number said for a dictated one.
    said: dict[int, list[int]] = {}
    for g in guide:
        for it in g.items:
            if it.operation == "dictate" and it.a is not None:
                said.setdefault(it.n, []).append(it.a)
    by_n: dict[int, list[ReadPaperItem]] = {}
    for r in reads:
        for it in r.items:
            by_n.setdefault(it.n, []).append(it)
    items = []
    for n in sorted(by_n):
        seen = by_n[n]
        votes = Counter((i.operation, i.a, i.b) for i in seen)
        (operation, a, b), _ = votes.most_common(1)[0]
        pick = next(i for i in seen if (i.operation, i.a, i.b) == (operation, a, b))
        disagree = len(votes) > 1
        merged = pick.model_copy(update={"unsure": pick.unsure or disagree})
        from_guide = False
        if operation == "dictate" and a is None and n in said:
            number, count = Counter(said[n]).most_common(1)[0]
            merged = merged.model_copy(
                update={"a": number, "unsure": merged.unsure or count < len(said[n])}
            )
            from_guide = True
        from_key = False
        if operation == "dictate" and merged.a is None and key and n in key:
            merged = merged.model_copy(update={"a": key[n]})
            from_key = True
        computed = compute_item(merged, drop_printed_answer=handwritten)
        computed["disagreement"] = disagree and not from_guide
        computed["from_guide"] = from_guide
        computed["from_key"] = from_key
        # An answer key file never sets an answer: code works it out, and a key that differs is flagged.
        if key and n in key:
            computed["key_file"] = key[n]
            if computed["correct"] is not None and computed["correct"] != key[n] and not from_key:
                computed["key_mismatch"] = True
        items.append(computed)
    first = reads[0]
    return {
        "header": {
            "form_letter": next((r.form_letter for r in reads if r.form_letter), None),
            "check_code": next((r.check_code for r in reads if r.check_code), None),
            "class_code": next((r.class_code for r in reads if r.class_code), None),
        },
        "language": first.language,
        "contains_handwritten_answers": handwritten,
        "sheets_read": len(reads),
        "items": items,
        "class_id": "shared",  # common to the block or school; no one is asked for a class
        "kind": None,
        "form": None,
    }


def recompute(draft: dict[str, Any]) -> dict[str, Any]:
    """After any edit: recompute every item (key, probes, wrong answers) and the coverage grid."""
    handwritten = bool(draft.get("contains_handwritten_answers"))
    items = []
    for it in draft["items"]:
        rebuilt = compute_item(
            ReadPaperItem(
                n=it["n"],
                operation=it["operation"],
                a=it["a"],
                b=it["b"],
                prompt_text=it.get("prompt_text", ""),
                box_pct=it.get("box_pct", []),
                printed_answer=it.get("printed_answer"),
                unsure=it.get("unsure", False),
            ),
            drop_printed_answer=handwritten,
        )
        rebuilt["user_excluded"] = bool(it.get("user_excluded", False))
        rebuilt["include"] = rebuilt["supported"] and not rebuilt["user_excluded"]
        rebuilt["disagreement"] = it.get("disagreement", False)
        rebuilt["acknowledged"] = it.get("acknowledged", False)
        # the number came from the guide until she changes it herself
        rebuilt["from_key"] = bool(it.get("from_key")) and f"items.{it['n']}.a" not in (
            draft.get("changes") or {}
        )
        if it.get("key_file") is not None:
            rebuilt["key_file"] = it["key_file"]
            if rebuilt["correct"] is not None and rebuilt["correct"] != it["key_file"]:
                rebuilt["key_mismatch"] = True
        rebuilt["from_guide"] = bool(it.get("from_guide")) and f"items.{it['n']}.a" not in (
            draft.get("changes") or {}
        )
        items.append(rebuilt)
    draft = {**draft, "items": items}
    draft["coverage"] = coverage(items)
    draft["coverage_warnings"] = coverage_warnings(draft["coverage"])
    draft["open_questions"] = open_questions(draft)
    return draft


def open_questions(draft: dict[str, Any]) -> list[dict[str, Any]]:
    """What is missing, as data. Each has an id, why it matters, options, whether it blocks Confirm,
    and the field it fills. The assistant asks these one at a time; a person always presses Confirm."""
    qs: list[dict[str, Any]] = []
    if draft.get("kind") not in ("pre", "post", "termly"):
        qs.append(
            _q(
                "kind",
                "A pre-test and a post-test are used differently.",
                ["pre", "post", "termly"],
                True,
                "kind",
            )
        )
    for it in draft["items"]:
        n = it["n"]
        if it["reason"] == "dictated_number_needed":
            qs.append(
                _q(
                    f"dictation-{n}",
                    f"Item {n} is dictated. Which number was said?",
                    None,
                    False,
                    f"items.{n}.a",
                )
            )
        elif not it["supported"]:
            qs.append(
                _q(
                    f"unsupported-{n}",
                    f"Item {n} is not a supported type yet.",
                    ["leave_out", "enter_by_hand"],
                    False,
                    f"items.{n}.include",
                )
            )
        elif it["unsure"] and it["include"]:
            qs.append(
                _q(
                    f"unsure-{n}",
                    f"The reader was unsure of the numbers in item {n}.",
                    None,
                    True,
                    f"items.{n}.operands",
                )
            )
        if it["key_mismatch"] and not it.get("acknowledged"):
            qs.append(
                _q(
                    f"key-{n}",
                    f"The printed answer for item {n} differs from the computed one.",
                    ["use_computed", "check_paper"],
                    True,
                    f"items.{n}.acknowledged",
                )
            )
    if not any(i["include"] for i in draft["items"]):
        qs.append(_q("no_items", "No item is included.", None, True, "items"))
    for code in draft.get("coverage_warnings", []):
        qs.append(
            _q(
                f"coverage-{code}",
                f"{code} is probed by fewer than two items, so diagnosis of it is limited.",
                ["continue", "add_item"],
                False,
                "coverage",
            )
        )
    return qs


def _q(qid: str, why: str, options: list[str] | None, blocking: bool, field: str) -> dict[str, Any]:
    return {"id": qid, "why": why, "options": options, "blocking": blocking, "field": field}


def blocking(draft: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in draft.get("open_questions", []) if q["blocking"]]
