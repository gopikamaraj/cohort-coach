"""Topic packs: validation, and the two-key lifecycle (coach approves, officer enables).

A pack is data. Validation checks it against the grammar and the content rules; the lifecycle
follows the same two-key rule as every other content: draft, then approved by a coach, then enabled
for the block by a programme officer. Every change is a new version; an enabled pack that is edited
stays in use until the new version is approved and enabled.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ai.validators.check_items import check_items
from services.api.sprites.avatar import expression_ids
from services.api.sprites.grammar import validate_spec
from services.api.sprites.items import load_item
from services.api.sprites.scene import LAYOUTS

STATUSES = ("draft", "approved", "enabled")
LANGS = ("en", "hi", "ta")
OPERATIONS = ("add", "sub", "parts")
SLOT = re.compile(r"\{(\w+)\}")


def validate_pack(pack: dict[str, Any], tables: dict[str, dict[str, str]]) -> list[str]:
    """Rule ids broken by a pack. `tables` maps a language to its strings."""
    out: list[str] = []
    if pack.get("status") not in STATUSES:
        out.append("bad_status")
    if not isinstance(pack.get("version"), int):
        out.append("bad_version")
    for item_id in pack.get("items", []):
        try:
            bad = validate_spec(load_item(item_id))
        except FileNotFoundError:
            out.append(f"unknown_item:{item_id}")
            continue
        out += [f"item:{item_id}:{b}" for b in bad]
    for layout in pack.get("layouts", []):
        if layout not in LAYOUTS:
            out.append(f"unknown_layout:{layout}")
    for expr in pack.get("expressions", []):
        if expr not in expression_ids():
            out.append(f"unknown_expression:{expr}")
    for tpl in pack.get("templates", []):
        if tpl.get("operation") not in OPERATIONS:
            out.append(f"bad_operation:{tpl.get('id')}")
        if tpl.get("layout") not in LAYOUTS:
            out.append(f"unknown_layout:{tpl.get('layout')}")
        if tpl.get("item") and tpl["item"] not in pack.get("items", []):
            out.append(f"item_not_in_pack:{tpl['item']}")
        for lang in LANGS:
            text = tables.get(lang, {}).get(tpl.get("text_key", ""))
            if not text:
                out.append(f"missing_text:{tpl.get('id')}:{lang}")
                continue
            if any(name not in ("a", "b") for name in SLOT.findall(text)):
                out.append(f"unknown_slot:{tpl['id']}:{lang}")
            if re.search(r"\d", text):
                out.append(
                    f"digit_in_template:{tpl['id']}:{lang}"
                )  # numbers are slots filled by code
            if check_items(text):
                out.append(f"check_item:{tpl['id']}:{lang}")
    return sorted(set(out))


# ------------------------------------------------------------------------------- lifecycle
def approve(pack: dict[str, Any], role: str) -> dict[str, Any]:
    """Gate 3: a coach approves a draft. Returns the next version."""
    if role != "coach":
        raise PermissionError("only a coach approves a pack")
    if pack["status"] != "draft":
        raise ValueError("only a draft can be approved")
    return {**deepcopy(pack), "status": "approved", "version": pack["version"] + 1}


def enable(pack: dict[str, Any], role: str) -> dict[str, Any]:
    """The programme officer enables an approved pack for the block. Returns the next version."""
    if role != "officer":
        raise PermissionError("only a programme officer enables a pack")
    if pack["status"] != "approved":
        raise ValueError("only an approved pack can be enabled")
    return {**deepcopy(pack), "status": "enabled", "version": pack["version"] + 1}


class PackShelf:
    """What a block runs. An edit makes a new draft; the enabled version stays in use until the
    new one has both keys."""

    def __init__(self, enabled: dict[str, Any]) -> None:
        self.in_use = enabled
        self.pending: dict[str, Any] | None = None
        self.history: list[tuple[int, str, str]] = [(enabled["version"], "enabled", "start")]

    def edit(self, changes: dict[str, Any]) -> dict[str, Any]:
        base = self.pending or self.in_use
        self.pending = {
            **deepcopy(base),
            **changes,
            "status": "draft",
            "version": base["version"] + 1,
        }
        self.history.append((self.pending["version"], "draft", "edit"))
        return self.pending

    def approve(self, role: str) -> None:
        assert self.pending is not None
        self.pending = approve(self.pending, role)
        self.history.append((self.pending["version"], "approved", role))

    def enable(self, role: str) -> None:
        assert self.pending is not None
        self.pending = enable(self.pending, role)
        self.in_use, self.pending = self.pending, None
        self.history.append((self.in_use["version"], "enabled", role))
