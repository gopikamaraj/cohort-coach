"""A new topic pack is data only: the renderer files stay exactly as they were recorded."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from services.api.sprites.items import item_ids, load_pack, pack_ids
from services.api.sprites.layouts import row
from services.api.sprites.palette import palette
from services.api.sprites.scene import SceneError, render_template

from .helpers import parse, units

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from sprite_renderer_hash import FIXTURE, renderer_hash  # noqa: E402


def test_the_renderer_is_byte_for_byte_what_it_was_when_the_second_pack_was_added() -> None:
    recorded = FIXTURE.read_text(encoding="ascii").strip()
    assert renderer_hash() == recorded, (
        "a renderer file changed: a new pack must need JSON only. If the change is deliberate, "
        "log it in DECISIONS.md and run scripts/sprite_renderer_hash.py --write"
    )


def test_the_second_pack_and_its_item_exist_as_json_only() -> None:
    assert "fractions-demo" in pack_ids() and "chapati" in item_ids()
    pack = load_pack("fractions-demo")
    assert pack["status"] == "draft"  # not approved, not enabled: never reaches a teacher


def test_the_new_item_draws_exact_counts_through_the_existing_layouts() -> None:
    from services.api.sprites.items import load_item

    spec = load_item("chapati")
    for n in (0, 1, 7, 23, 100):
        scene = row(spec, n, palette("default"))
        assert scene.report["count_drawn"] == n and len(units(parse(scene.svg))) == n


def test_the_draft_pack_is_refused_for_teachers_until_both_keys() -> None:
    with pytest.raises(SceneError, match="enabled pack"):
        render_template("fractions-demo", "share_chapati", 4, 2)
