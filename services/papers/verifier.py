"""The independent verifier: re-checks a paper before anyone sees it.

It shares no code with the generator or the engine (tests/papers/test_verifier.py reads this
file's imports to prove it). Every key and every wrong answer is recomputed here from the operands
with its own digit arithmetic, so a mistake in the generator or in engine/bugs.py shows up as a
disagreement. Any finding blocks approval and names the item and the rule.

Rules checked: key, wrong_answers, wrong_equals_key, coverage, discrimination, duplicate, twin,
strings, glyphs, overflow, overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont  # type: ignore[import-untyped]

FONT_DIR = Path(__file__).with_name("fonts")
LATIN = [FONT_DIR / "NotoSans-Regular.ttf", FONT_DIR / "NotoSans-Bold.ttf"]
FONTS: dict[str, list[Path]] = {
    "en": LATIN,
    "hi": LATIN + [FONT_DIR / "NotoSansDevanagari-Regular.ttf"],
    "ta": LATIN + [FONT_DIR / "NotoSansTamil-Regular.ttf"],
}
COMPETENCY_OF = {
    "PV-HEARD": "C1",
    "PV-REVERSE": "C1",
    "ADD-NOCARRY": "C2",
    "SUB-SFL": "C3",
    "SUB-NODEC": "C3",
}
MIN_PROBES = 2
EDGE_MM = 5.0  # nothing printed closer than this to the paper's edge


@dataclass(frozen=True)
class Finding:
    rule: str
    item: int | None
    detail: str


# --- independent arithmetic (digit strings, no shared code) ------------------------------


def _no_zero(n: int) -> str | None:
    s = str(n)
    return s if len(s) in (2, 3) and "0" not in s else None


def _heard(n: int) -> set[int]:
    s = _no_zero(n)
    if s is None:
        return set()
    if len(s) == 2:
        return {int(s[0] + "0" + s[1])}
    h, t, o = s[0], s[1], s[2]
    return {int(h + "00" + t + o), int(h + "0" + t + o), int(h + "00" + t + "0" + o)}


def _reverse(n: int) -> set[int]:
    s = _no_zero(n)
    return set() if s is None else {int(s[:-2] + s[-1] + s[-2])}


def _columns(a: int, b: int) -> tuple[str, str]:
    return str(a).rjust(2, "0"), str(b).rjust(2, "0")


def _expected(op: str, a: int, b: int) -> tuple[int, dict[str, set[int]], dict[str, set[int]]]:
    """(key, tracked wrong answers by code, untracked wrong answers by code)."""
    if op == "dictate":
        key = a
        both = set().union(*(_heard(r) for r in _reverse(a))) if _reverse(a) else set()
        wrong = {"PV-HEARD": _heard(a) | both, "PV-REVERSE": _reverse(a) | both}
        return key, wrong, {}
    x, y = _columns(a, b)
    if op == "add":
        key = a + b
        ones = int(x[1]) + int(y[1])
        if ones < 10:
            return key, {}, {}
        no_carry = int(str(int(x[0]) + int(y[0])) + str(ones % 10))
        whole = int(str(int(x[0]) + int(y[0])) + str(ones))
        return key, {"ADD-NOCARRY": {no_carry}}, {"ADD-WHOLE-ONES": {whole}}
    key = a - b
    if int(x[1]) >= int(y[1]):
        return key, {}, {}
    sfl = int(str(abs(int(x[0]) - int(y[0]))) + str(abs(int(x[1]) - int(y[1]))))
    nodec = int(str(int(x[0]) - int(y[0]))) * 10 + (int(x[1]) + 10 - int(y[1]))
    return key, {"SUB-SFL": {sfl}, "SUB-NODEC": {nodec}}, {}


def _shape(op: str, a: int, b: int) -> tuple[str, int, bool]:
    """What a twin must keep: operation, difficulty (digits, ones total or ones gap), and whether
    it carries or borrows."""
    if op == "dictate":
        return op, len(str(a)), False
    if op == "add":
        return op, a % 10 + b % 10, a % 10 + b % 10 >= 10
    borrow = a % 10 < b % 10
    return op, (b % 10 - a % 10) if borrow else 0, borrow


# --- checks --------------------------------------------------------------------------------


def verify_items(paper: dict[str, Any], twin_source: dict[str, Any] | None = None) -> list[Finding]:
    out: list[Finding] = []
    items = paper["items"]
    probes: dict[str, list[int]] = {}
    seen: dict[tuple[str, int, int], int] = {}
    for it in items:
        n, op, a, b = it["n"], it["operation"], it["a"], it["b"]
        key, wrong, untracked = _expected(op, a, b)
        if it["correct"] != key:
            out.append(Finding("key", n, f"key is {it['correct']}, the operands give {key}"))
        for code, answers in wrong.items():
            answers.discard(key)
            if it["correct"] in {int(x) for x in it["wrong"].get(code, [])}:
                out.append(Finding("wrong_equals_key", n, f"{code} lists the key {it['correct']}"))
            if sorted(answers) != sorted(int(x) for x in it["wrong"].get(code, [])):
                out.append(
                    Finding(
                        "wrong_answers",
                        n,
                        f"{code} wrong answers are {it['wrong'].get(code)}, "
                        f"recomputed {sorted(answers)}",
                    )
                )
            if answers:
                probes.setdefault(code, []).append(n)
        for code in set(it["wrong"]) - set(wrong):
            out.append(Finding("wrong_answers", n, f"{code} does not apply to this item"))
        # Discrimination: no wrong answer may count for two errors, except the designed
        # heard-and-reversed answer that counts for both place-value errors.
        owner: dict[int, str] = {}
        for code, answers in wrong.items():
            for ans in answers:
                if ans in owner and {owner[ans], code} != {"PV-HEARD", "PV-REVERSE"}:
                    out.append(
                        Finding(
                            "discrimination",
                            n,
                            f"{owner[ans]} and {code} both give {ans}: the item cannot tell them "
                            "apart",
                        )
                    )
                owner[ans] = code
        for code, answers in untracked.items():
            for ans in answers & set(owner):
                out.append(Finding("discrimination", n, f"{code} {ans} collides with {owner[ans]}"))
        k = (op, a, b)
        if k in seen:
            out.append(Finding("duplicate", n, f"repeats item {seen[k]} ({a}, {b})"))
        seen.setdefault(k, n)
    not_assessed = set(paper.get("not_assessed") or [])
    for code, comp in COMPETENCY_OF.items():
        if comp in not_assessed:
            continue
        got = len(probes.get(code, []))
        if got < MIN_PROBES:
            out.append(
                Finding("coverage", None, f"{code} is probed by {got} item(s), needs {MIN_PROBES}")
            )
    if twin_source is not None:
        out += _verify_twin(paper, twin_source)
    return out


def _verify_twin(paper: dict[str, Any], source: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    src = {i["n"]: i for i in source["items"]}
    pairs = {(i["a"], i["b"]) for i in source["items"]}
    if len(paper["items"]) != len(source["items"]):
        out.append(
            Finding(
                "twin",
                None,
                f"{len(paper['items'])} items, the paper it twins has {len(source['items'])}",
            )
        )
    for it in paper["items"]:
        n, partner = it["n"], src.get(it.get("twin_of") or -1)
        if partner is None:
            out.append(Finding("twin", n, "has no twin on the first paper"))
            continue
        if _shape(it["operation"], it["a"], it["b"]) != _shape(
            partner["operation"], partner["a"], partner["b"]
        ):
            out.append(Finding("twin", n, f"does not match item {partner['n']} in skill or level"))
        if (it["a"], it["b"]) in pairs:
            out.append(Finding("twin", n, f"repeats the number pair {it['a']}, {it['b']}"))
        if it.get("is_anchor") != partner.get("is_anchor"):
            out.append(Finding("twin", n, "anchor and adaptive do not match"))
    return out


@cache
def _cmap(path: Path) -> frozenset[int]:
    font = TTFont(str(path), lazy=True)
    return frozenset(font.getBestCmap() or {})


def verify_strings(packs: dict[str, dict[str, str]], fonts: dict[str, list[Path]]) -> list[Finding]:
    """Every string present in every language, and every character in the fonts for it."""
    out: list[Finding] = []
    keys = set().union(*(set(p) for p in packs.values()))
    for lang, pack in sorted(packs.items()):
        for k in sorted(keys - {k for k, s in pack.items() if s.strip()}):
            out.append(Finding("strings", None, f"{lang} has no text for {k}"))
        covered = frozenset().union(*(_cmap(p) for p in fonts.get(lang, LATIN)))
        for k, s in sorted(pack.items()):
            missing = sorted({ch for ch in s if not ch.isspace() and ord(ch) not in covered})
            if missing:
                out.append(Finding("glyphs", None, f"{lang} {k}: no glyph for {''.join(missing)}"))
    return out


def verify_layout(layout: dict[str, Any]) -> list[Finding]:
    """Boxes inside the printable page, no two boxes overlapping, no text spilling out."""
    out: list[Finding] = []
    w, h = layout["page"]["w"], layout["page"]["h"]
    boxes = layout["boxes"]
    for bx in boxes:
        if (
            bx["x"] < EDGE_MM
            or bx["y"] < EDGE_MM
            or bx["x"] + bx["w"] > w - EDGE_MM
            or bx["y"] + bx["h"] > h - EDGE_MM
        ):
            out.append(Finding("overflow", None, f"{bx['id']} runs off page {bx['page']}"))
    for i, p in enumerate(boxes):
        for q in boxes[i + 1 :]:
            if p["page"] != q["page"]:
                continue
            if (
                p["x"] < q["x"] + q["w"]
                and q["x"] < p["x"] + p["w"]
                and p["y"] < q["y"] + q["h"]
                and q["y"] < p["y"] + p["h"]
            ):
                out.append(Finding("overlap", None, f"{p['id']} overlaps {q['id']}"))
    for o in layout.get("overflow", []):
        out.append(
            Finding(
                "overflow",
                None,
                f"text {o['id']} needs {o['need_mm']:.1f} mm, has {o['have_mm']:.1f} mm",
            )
        )
    return out
