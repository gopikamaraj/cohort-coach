"""Copy for every channel: the same `strings/{en,hi,ta}.json` the web app uses.

Flows and adapters carry string KEYS and slot values, never sentences; this module turns them into
text in the teacher's language. A missing key falls back to English and is remembered so
`python scripts/i18n.py todo` can list it. Slots are filled by code with values the code computed;
a param named `x_key` is a string key whose text fills the slot `x`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.api.flows.steps import Flow, Step

STRINGS = Path(__file__).resolve().parents[2] / "strings"
LANGS = ("en", "hi", "ta")
missing: set[str] = set()


@cache
def table(lang: str) -> Mapping[str, str]:
    return json.loads(
        (STRINGS / f"{lang if lang in LANGS else 'en'}.json").read_text(encoding="utf-8")
    )  # type: ignore[no-any-return]


def text(lang: str, key: str, **params: Any) -> str:
    value = table(lang).get(key)
    if not value:
        missing.add(f"{lang}:{key}")
        value = table("en").get(key, key)
    slots = dict(params)
    for name, val in params.items():
        if name.endswith("_key"):
            slots[name[:-4]] = text(lang, str(val))
    return re.sub(r"\{(\w+)\}", lambda m: str(slots.get(m.group(1), m.group(0))), value)


def render(step: Step, lang: str) -> str:
    """A step's main text, with a "Simulated data" line when the step shows synthetic data."""
    extra = [text(lang, ln.copy, **ln.params) for ln in step.lines]
    body = "\n".join([text(lang, step.copy, **step.params), *extra])
    return f"{text(lang, 'common.simulated')}: {body}" if step.simulated else body


def keys_used_by(flows: Iterable[Flow] | Mapping[str, Flow]) -> list[str]:
    items = flows.values() if isinstance(flows, Mapping) else flows
    keys: set[str] = {"common.simulated"}
    for flow in items:
        for node in flow.nodes.values():
            keys.update(node.keys)
    return sorted(keys)
