"""Intervention adapter: structured content in, a spoken script out. No AI call.

The sections are built the way the page builds them (apps/pwa/src/lib/pack.ts) from the same
three files, but as listening text: a short lead-in instead of a title, one idea per sentence,
steps spoken as "Step one", a pause after anything the teacher has to do, no Source or Draft tags
and no labels. Numbers about her class are said as words; a place-value example is marked {pv:N}
so it is read digit by digit. When the language asked for has no text for part of the content,
the whole script is made in English (as the page does) and `fallback` is set.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.diagnosis import MIN_HITS
from services.content import error_content
from services.spoken.lang import pack_for
from services.spoken.normalizer import normalize
from services.spoken.schema import PAUSE_LONG, PAUSE_SHORT, SpokenScript, Utterance, version_hash
from services.spoken.validators import config, speaker_config, validate, words_in

ROOT = Path(__file__).resolve().parents[3]
MAX_STRATEGIES = 3
MAX_ROLLS = 8
SPEAKER = "narrator"


class _Fallback(Exception):
    """The language has no text for a piece: the caller rebuilds in English."""


def _pick(field: Any, lang: str, *, optional: bool = False) -> Any:
    if not field:
        return None
    if lang in field and field[lang]:
        return field[lang]
    if lang != "en":
        raise _Fallback
    return field.get("en") if "en" in field else None


def _split_long(text: str, limit: int) -> str:
    """Cut a sentence that is too long for the ear at a comma or " and " near its middle."""
    out: list[str] = []
    for s in re.split(r"(?<=[.?!।])\s+", text.strip()):
        if words_in(s) <= limit:
            out.append(s)
            continue
        words = s.split()
        mid = len(words) // 2
        cuts = [
            i for i, w in enumerate(words[:-1]) if w.endswith(",") or words[i + 1].lower() == "and"
        ]
        if cuts:
            i = min(cuts, key=lambda c: abs(c - mid))
            first, rest = words[: i + 1], words[i + 1 :]
            first[-1] = first[-1].rstrip(",")
            if rest and rest[0].lower() == "and":
                rest = rest[1:]
            if rest:
                rest[0] = rest[0][:1].upper() + rest[0][1:]
            out.append(" ".join(first) + ".")
            out.append(_split_long(" ".join(rest), limit))
        else:
            out.append(s)
    return " ".join(out)


def _sentences(text: str, limit: int) -> list[str]:
    return [s for s in re.split(r"(?<=[.?!।])\s+", _split_long(text, limit)) if s.strip()]


def content_hash() -> str:
    files = [
        error_content.ERRORS / "explanations.v1.yaml",
        error_content.ERRORS / "intervention.v1.yaml",
        error_content.STRATEGIES,
        ROOT / "content" / "spoken.yaml",
    ]
    return version_hash(*(f.read_bytes().hex()[:4096] + str(f.stat().st_size) for f in files))


def _strategies(
    code: str, iv: dict[str, Any], lib: dict[str, Any], lang: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid, s in lib["strategies"].items():
        if code not in s["fits"]:
            continue
        detail = iv["strategy_details"].get(sid, {})
        label, desc, steps = (
            _pick(s["label"], lang),
            _pick(s["description"], lang),
            _pick(detail.get("steps"), lang),
        )
        if not (label and desc and steps):
            continue
        out.append(
            {
                "label": label,
                "desc": desc,
                "steps": steps,
                "materials": _pick(detail.get("materials"), lang),
                "worked": s.get("worked_examples", []),
            }
        )
    for x in iv.get("extra_strategies", {}).get(code, []):
        label, desc, steps = (
            _pick(x["label"], lang),
            _pick(x["description"], lang),
            _pick(x["steps"], lang),
        )
        if label and desc and steps:
            out.append(
                {
                    "label": label,
                    "desc": desc,
                    "steps": steps,
                    "materials": _pick(x.get("materials"), lang),
                    "worked": [],
                }
            )
    return out[:MAX_STRATEGIES]


def _rolls(numbers: list[int], pack: Any) -> str:
    shown = [str(n) for n in numbers[:MAX_ROLLS]]
    text = ", ".join(shown)
    if len(numbers) > MAX_ROLLS:
        text += ", " + pack.phrases["and_more"].format(n=len(numbers) - MAX_ROLLS)
    return text


def _build(
    code: str,
    lang: str,
    children: int,
    total: int,
    rolls: dict[str, list[int]] | None,
    example: dict[str, str] | None,
) -> list[Utterance]:
    ex, iv, lib = (
        error_content.explanations()["errors"].get(code),
        error_content.intervention()["errors"].get(code),
        error_content.strategies(),
    )
    if ex is None and iv is None:
        raise ValueError(f"no content for {code}")
    pack = pack_for(lang)
    limit = int(speaker_config(SPEAKER)["max_sentence_words"])
    ph = pack.phrases
    sections: list[tuple[str, list[str]]] = []

    def add(sid: str, lines: list[str]) -> None:
        lines = [x for x in lines if x and x.strip()]
        if lines:
            sections.append((sid, lines))

    # what she is seeing: the class's own counts
    what = _pick((ex or {}).get("what"), lang) or ""
    seeing = [
        ph["of_class"].format(ratio=pack.ratio_phrase(children, total))
        + ("." if lang != "hi" else "।")
    ]
    if rolls and rolls.get("confirmed"):
        seeing.append(
            ph["rolls"].format(list=_rolls(rolls["confirmed"], pack))
            + ("." if lang != "hi" else "।")
        )
    if rolls and rolls.get("possible"):
        seeing.append(
            ph["rolls_possible"].format(list=_rolls(rolls["possible"], pack))
            + ("." if lang != "hi" else "।")
        )
    if example and example.get("wrote") and example.get("correct") and example.get("question"):

        def pv(v: str) -> str:
            return "{pv:" + v + "}" if re.fullmatch(r"\d+", v or "") else v

        seeing.append(
            ph["example_say"].format(
                question=example["question"],
                wrote=pv(example["wrote"]),
                correct=pv(example["correct"]),
            )
        )
    if what:
        seeing = [f"{what}"] + seeing
    add("seeing", [*_sentences(" ".join(seeing), limit)])

    add("why", [ph["why"], *_sentences(_pick((ex or {}).get("why"), lang) or "", limit)])
    check = _pick((iv or {}).get("two_minute_check"), lang)
    add("check", [ph["check"], *_sentences(check or "", limit), PAUSE_LONG] if check else [])

    chosen = _strategies(code, error_content.intervention(), lib, lang)
    if chosen:
        lines = [ph["strategies"]]
        for i, s in enumerate(chosen, 1):
            lines.append(ph["strategy"].format(i=pack.number_to_words(i), label=s["label"]))
            lines += _sentences(s["desc"], limit)
            if s["materials"] and str(s["materials"]).strip().lower() != "none":
                lines.append(ph["materials"].format(list=str(s["materials"]).rstrip(".")))
            for n, step in enumerate(s["steps"], 1):
                lines.append(ph["step"].format(i=pack.number_to_words(n)))
                lines += _sentences(step, limit)
                lines.append(PAUSE_SHORT)
            # worked examples are sums with English words, not translated: other languages skip them
            for w in s["worked"][:1] if lang == "en" else []:
                lines += _sentences(ph["example"].format(text=str(w).rstrip(".")), limit)
            lines.append(PAUSE_LONG)
        add("strategies", lines)

    activity = _pick((iv or {}).get("ten_minute_activity"), lang)
    add(
        "activity",
        [ph["activity"], *_sentences(activity or "", limit), PAUSE_LONG] if activity else [],
    )
    mistakes = _pick((iv or {}).get("teaching_mistakes"), lang)
    add(
        "mistakes",
        [ph["mistakes"], *[s for m in (mistakes or []) for s in _sentences(m, limit)]]
        if mistakes
        else [],
    )
    n_hits = MIN_HITS  # the check's own rule, read from the engine
    add(
        "working",
        [
            ph["working"],
            *_sentences(
                ph["working_line"].format(
                    n=pack.number_to_words(n_hits), ratio=pack.ratio_phrase(children, total)
                ),
                limit,
            ),
        ],
    )
    home = _pick((iv or {}).get("at_home"), lang)
    add(
        "home",
        [ph["home"], *[s for m in (home or []) for s in _sentences(m, limit)]] if home else [],
    )
    stuck = _pick((iv or {}).get("if_not_improving"), lang)
    add("stuck", [ph["stuck"], *_sentences(stuck or "", limit)] if stuck else [])

    return [
        Utterance(f"{code}:{sid}", SPEAKER, normalize("\n".join(lines), lang))
        for sid, lines in sections
    ]


def build_script(
    code: str,
    language: str,
    children: int,
    total: int,
    rolls: dict[str, list[int]] | None = None,
    example: dict[str, str] | None = None,
) -> SpokenScript:
    """The spoken script for one error of a cohort. Counts come from the caller (code computed
    them); nothing here makes a number up. Falls back to English as a whole when needed."""
    fallback = False
    lang = language
    try:
        uts = _build(code, lang, children, total, rolls, example)
    except _Fallback:
        lang, fallback = "en", True
        uts = _build(code, lang, children, total, rolls, example)
    words = sum(u.words for u in uts)
    cfg = speaker_config(SPEAKER)
    pauses = (
        sum(
            t.count(PAUSE_SHORT) * config()["pauses_ms"]["short"]
            + t.count(PAUSE_LONG) * config()["pauses_ms"]["long"]
            for t in (u.text for u in uts)
        )
        / 1000
    )
    issues = tuple(str(i) for u in uts for i in validate(u.text, lang, SPEAKER))
    return SpokenScript(
        surface="intervention",
        language=lang,
        speaker=SPEAKER,
        content_version_hash=content_hash(),
        utterances=tuple(uts),
        total_words=words,
        est_seconds=round(words / float(cfg["words_per_second"]) + pauses, 1),
        fallback=fallback,
        issues=issues,
    )
