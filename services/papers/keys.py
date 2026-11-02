"""A paper's own answer key, in the shape the phone's error finder already reads.

The phone does not know a paper by a form letter: it is given the key of the paper that was chosen
for the check (each item's right answer, the wrong answer each error would give, which errors the
item probes, and the stage signatures). Every one of those is computed by the engine from the
paper's own numbers, the same way `engine.export_keys` does for the built-in forms. Nothing is
decided here by a model.
"""

from __future__ import annotations

from typing import Any

from engine.export_keys import build_answer_keys
from engine.model import Form, Item, ItemType


def form_of(body: dict[str, Any], label: str) -> Form:
    """The engine's form for a paper: dictation, addition, a subtraction that needs no borrowing
    (the anchor) or one that does. The type follows from the numbers, so a generated paper and an
    imported one are read alike."""
    items: list[Item] = []
    for it in body["items"]:
        op, a, b = it["operation"], int(it["a"]), int(it.get("b") or 0)
        if op == "dictate":
            items.append(Item(int(it["n"]), ItemType.DICTATION, a))
        elif op == "add":
            items.append(Item(int(it["n"]), ItemType.ADD_CARRY, a, b))
        else:
            kind = ItemType.SUB_BORROW if a % 10 < b % 10 else ItemType.SUB_ANCHOR
            items.append(Item(int(it["n"]), kind, a, b))
    return Form(label, tuple(items))


def key_of(paper_id: str, body: dict[str, Any], label: str) -> dict[str, Any]:
    """`{forms: {<paper id>: {label, items}}, rules, ...}` for one paper. Each item also says
    whether it is an anchor: adaptive items help find errors but never count in before and after.
    An imported paper has no adaptive items, so every item is an anchor."""
    key = build_answer_keys({paper_id: form_of(body, label)})
    imported = body.get("source") == "imported_pdf"
    anchors = {int(it["n"]): imported or bool(it.get("is_anchor", True)) for it in body["items"]}
    for item in key["forms"][paper_id]["items"]:
        item["anchor"] = anchors.get(int(item["n"]), True)
    return key
