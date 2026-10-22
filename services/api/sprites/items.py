"""Loading item specs and topic packs from content/sprites (data, owned by Seema)."""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from services.api.sprites.palette import SPRITES


@cache
def load_item(item_id: str) -> dict[str, Any]:
    path = SPRITES / "items" / f"{item_id}.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def item_ids() -> list[str]:
    return sorted(p.name.split(".")[0] for p in (SPRITES / "items").glob("*.v1.json"))


@cache
def load_pack(pack_id: str) -> dict[str, Any]:
    path = SPRITES / "packs" / f"{pack_id}.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def pack_ids() -> list[str]:
    return sorted(p.name.split(".")[0] for p in (SPRITES / "packs").glob("*.v1.json"))
