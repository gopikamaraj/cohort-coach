"""Sprite scenes for the channels: resolve a scene reference, draw it, and make the PNG.

Only a scene from an enabled pack, with an item and a layout that pack lists, is drawn. A reference
to anything else raises ValueError and the channel shows the text alone. The web app draws the same
reference itself with the TypeScript renderer (byte-identical, proven by the golden fixture).
"""

from __future__ import annotations

from services.api.flows.steps import SceneRef
from services.api.sprites.items import load_pack
from services.api.sprites.layouts import Scene
from services.api.sprites.palette import palette
from services.api.sprites.png import svg_to_png
from services.api.sprites.scene import SceneError, render_layout


def resolve(ref: SceneRef) -> Scene:
    try:
        pack = load_pack(ref.pack)
    except FileNotFoundError as exc:
        raise ValueError(f"unknown pack {ref.pack!r}") from exc
    if pack.get("status") != "enabled":
        raise ValueError("only an enabled pack reaches a teacher")
    if ref.layout not in pack.get("layouts", []):
        raise ValueError(f"the pack does not list the layout {ref.layout!r}")
    if ref.item is not None and ref.item not in pack.get("items", []):
        raise ValueError(f"the pack does not list the item {ref.item!r}")
    try:
        return render_layout(ref.layout, ref.item, dict(ref.args), palette(ref.palette), ref.seed)
    except (SceneError, KeyError) as exc:
        raise ValueError(str(exc)) from exc


def scene_png(ref: SceneRef, width: int = 480) -> bytes:
    return svg_to_png(resolve(ref).svg, width=width)


TRAY_PACK = "place-value-add-sub"


def tray_items(materials: list[str]) -> dict[str, str]:
    """Which sprite item draws each Practice Class tray material. Only from an enabled pack, and
    only an item that pack lists; anything else is left out and the tray shows its word alone."""
    try:
        pack = load_pack(TRAY_PACK)
    except FileNotFoundError:
        return {}
    if pack.get("status") != "enabled":
        return {}
    tray = pack.get("tray", {})
    return {m: tray[m] for m in materials if tray.get(m) in pack.get("items", [])}
