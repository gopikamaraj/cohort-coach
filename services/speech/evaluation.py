"""Speech evaluation (Prompt 4): blinding the listening pack, aggregating raters' scores,
speech-to-text metrics, and the two gates that decide whether Bodhan may be first.

Every number here is computed by code from raters' CSV files or transcripts; nothing is estimated by
an AI. The thresholds are in content/speech_gates.yaml (TODO-HUMAN to confirm). A gate is written to
docs/evidence/speech_gates.md only when a person passes --record with their name.
"""

from __future__ import annotations

import csv
import random
import re
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from services.speech import textnorm

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "content" / "speech_eval" / "scripts.yaml"
THRESHOLDS = ROOT / "content" / "speech_gates.yaml"
GATES = ROOT / "docs" / "evidence" / "speech_gates.md"
SCORES = ("naturalness", "clarity", "numbers", "suitability")


@cache
def scripts() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(SCRIPTS.read_text(encoding="utf-8"))
    return data


@cache
def thresholds() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(THRESHOLDS.read_text(encoding="utf-8"))
    return data


# --- the listening pack: blinding -----------------------------------------------------------------


@dataclass(frozen=True)
class Clip:
    language: str
    kind: str  # lesson | child
    index: int
    text: str
    provider: str
    voice: str
    style: str | None


def blind(clips: Sequence[Clip], seed: int) -> tuple[list[tuple[str, Clip]], list[dict[str, Any]]]:
    """Random, meaningless file names in a shuffled order, and the key that maps them back. The key
    is written to its own file and never shown to raters."""
    rng = random.Random(seed)
    order = list(clips)
    rng.shuffle(order)
    names = rng.sample(range(10_000, 100_000), len(order))
    named = [(f"clip-{n}", c) for n, c in zip(names, order, strict=True)]
    key = [
        {
            "clip": name,
            "language": c.language,
            "kind": c.kind,
            "index": c.index,
            "provider": c.provider,
            "voice": c.voice,
            "style": c.style or "",
        }
        for name, c in named
    ]
    return named, key


# --- aggregating the raters' scores ---------------------------------------------------------------


def read_ratings(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for p in paths:
        with p.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.append({**r, "_file": p.name})
    return rows


def aggregate(
    ratings: Sequence[Mapping[str, str]], key: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Means per provider, per provider and voice, and per provider and language; the share of
    clips rated "numbers wrong" (a numbers score at or below the threshold). Ratings for clips not
    in the key, or with a score outside 1 to 5, are counted as rejected and left out."""
    by_clip = {k["clip"]: k for k in key}
    wrong_at = int(thresholds()["tts"]["numbers_wrong_at_or_below"])
    groups: dict[str, dict[tuple[str, ...], list[dict[str, float]]]] = {
        "provider": {},
        "provider_voice": {},
        "provider_language": {},
    }
    rejected = 0
    for r in ratings:
        k = by_clip.get(str(r.get("clip", "")).strip())
        try:
            scores = {s: float(r[s]) for s in SCORES}
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        if k is None or not all(1 <= v <= 5 for v in scores.values()):
            rejected += 1
            continue
        scores["numbers_wrong"] = 1.0 if scores["numbers"] <= wrong_at else 0.0
        groups["provider"].setdefault((k["provider"],), []).append(scores)
        groups["provider_voice"].setdefault((k["provider"], k["voice"]), []).append(scores)
        groups["provider_language"].setdefault((k["provider"], k["language"]), []).append(scores)
    out: dict[str, Any] = {"rejected": rejected}
    for name, g in groups.items():
        out[name] = {
            " / ".join(key_): {
                "ratings": len(rows),
                **{s: round(statistics.fmean(x[s] for x in rows), 3) for s in SCORES},
                "numbers_wrong_share": round(statistics.fmean(x["numbers_wrong"] for x in rows), 4),
            }
            for key_, rows in sorted(g.items())
        }
    return out


def tts_gate(agg: Mapping[str, Any]) -> dict[str, Any]:
    """Bodhan's mean naturalness within `naturalness_within` of Sarvam's, and its numbers-wrong
    share under the limit. `pending` when either provider has no ratings."""
    t = thresholds()["tts"]
    b = agg.get("provider", {}).get("bodhan")
    s = agg.get("provider", {}).get("sarvam")
    if not b or not s:
        return {"result": "pending", "why": "needs ratings for both Bodhan and Sarvam"}
    gap = round(s["naturalness"] - b["naturalness"], 3)
    checks = {
        "naturalness_gap": {
            "value": gap,
            "limit": t["naturalness_within"],
            "ok": gap <= t["naturalness_within"],
        },
        "numbers_wrong_share": {
            "value": b["numbers_wrong_share"],
            "limit": t["numbers_wrong_max_share"],
            "ok": b["numbers_wrong_share"] < t["numbers_wrong_max_share"],
        },
    }
    return {"result": "pass" if all(c["ok"] for c in checks.values()) else "fail", "checks": checks}


# --- speech to text ------------------------------------------------------------------------------


def key_terms(language: str) -> list[str]:
    return [str(t) for t in scripts()["key_terms"].get(language, [])]


def stt_item(reference: str, heard: str, language: str) -> dict[str, Any]:
    """Error rates after normalising digits and number words, whether every number in the reference
    was heard, and the key maths terms in the reference that were heard."""
    ref_n = textnorm.numbers_in(reference, language)
    hyp_n = textnorm.numbers_in(heard, language)
    rest = list(hyp_n)
    numbers_ok = 0
    for n in ref_n:
        if n in rest:
            numbers_ok += 1
            rest.remove(n)
    # key terms on text without the number conversion ("ten" is a term, and also a number)
    ref_norm = textnorm.normalise(reference, language, numbers=False)
    hyp_norm = textnorm.normalise(heard, language, numbers=False)

    def has(term: str, text: str) -> bool:  # a whole word: "ten" is not "tens" or "tents"
        return re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text) is not None

    terms = [t for t in key_terms(language) if has(t, ref_norm)]
    heard_terms = [t for t in terms if has(t, hyp_norm)]
    return {
        "cer": round(textnorm.cer(reference, heard, language), 4),
        "wer": round(textnorm.wer(reference, heard, language), 4),
        "numbers": len(ref_n),
        "numbers_ok": numbers_ok,
        "terms": len(terms),
        "terms_ok": len(heard_terms),
    }


def stt_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per provider (and per provider and language, and per tag): mean CER and WER, number accuracy
    and key-term accuracy (shares of all numbers and terms)."""

    def summ(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        n = sum(int(i["numbers"]) for i in items)
        t = sum(int(i["terms"]) for i in items)
        return {
            "items": len(items),
            "cer": round(statistics.fmean(float(i["cer"]) for i in items), 4),
            "wer": round(statistics.fmean(float(i["wer"]) for i in items), 4),
            "number_accuracy": round(sum(int(i["numbers_ok"]) for i in items) / n, 4)
            if n
            else None,
            "key_term_accuracy": round(sum(int(i["terms_ok"]) for i in items) / t, 4)
            if t
            else None,
        }

    out: dict[str, Any] = {"provider": {}, "provider_language": {}, "provider_tag": {}}
    for prov in sorted({str(r["provider"]) for r in rows}):
        mine = [r for r in rows if r["provider"] == prov]
        out["provider"][prov] = summ(mine)
        for lang in sorted({str(r["language"]) for r in mine}):
            out["provider_language"][f"{prov} / {lang}"] = summ(
                [r for r in mine if r["language"] == lang]
            )
        for tag in sorted({t for r in mine for t in str(r.get("tags", "")).split(";") if t}):
            tagged = [r for r in mine if tag in str(r.get("tags", "")).split(";")]
            out["provider_tag"][f"{prov} / {tag}"] = summ(tagged)
    return out


def stt_gate(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = thresholds()["stt"]
    b = summary.get("provider", {}).get("bodhan")
    s = summary.get("provider", {}).get("sarvam")
    if not b or not s:
        return {"result": "pending", "why": "needs transcripts from both Bodhan and Sarvam"}
    worse = round((b["cer"] - s["cer"]) * 100, 2)
    kt = b["key_term_accuracy"]
    checks = {
        "cer_worse_points": {
            "value": worse,
            "limit": t["cer_worse_max_points"],
            "ok": worse <= t["cer_worse_max_points"],
        },
        "key_term_accuracy": {
            "value": kt,
            "limit": t["key_term_accuracy_min"],
            "ok": kt is not None and kt >= t["key_term_accuracy_min"],
        },
    }
    return {"result": "pass" if all(c["ok"] for c in checks.values()) else "fail", "checks": checks}


def worst(rows: Sequence[Mapping[str, Any]], n: int = 10) -> list[Mapping[str, Any]]:
    return sorted(rows, key=lambda r: (-float(r["cer"]), str(r.get("id", ""))))[:n]


# --- the gates file -------------------------------------------------------------------------------


def read_gates(path: Path | None = None) -> dict[str, str]:
    path = path or GATES
    out = {"bodhan_tts": "pending", "bodhan_stt": "pending", "date": "", "decided_by": ""}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    if text.startswith("---") and text.count("---") >= 2:
        for line in text.split("---")[1].splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                if k.strip() in out:
                    out[k.strip()] = v.strip()
    return out


def record(
    gate: str, result: str, who: str, path: Path | None = None, details: str = ""
) -> dict[str, str]:
    """Write one gate's result (pass or fail) with the date and the person who decided. Only called
    when a person passes --record NAME; a pending result is never recorded."""
    if gate not in ("bodhan_tts", "bodhan_stt"):
        raise ValueError("gate must be bodhan_tts or bodhan_stt")
    if result not in ("pass", "fail"):
        raise ValueError("only a pass or a fail is recorded")
    if not who.strip():
        raise ValueError("--record needs the name of the person who decided")
    path = path or GATES
    state = read_gates(path)
    state[gate] = result
    state["date"] = date.today().isoformat()
    state["decided_by"] = who.strip()
    body = (
        path.read_text(encoding="utf-8").split("---", 2)[2]
        if path.exists() and path.read_text(encoding="utf-8").startswith("---")
        else ""
    )
    if details:
        body = (
            body.rstrip()
            + f"\n\n## {gate} recorded {state['date']} by {state['decided_by']}\n\n{details}\n"
        )
    front = "\n".join(
        f"{k}: {state[k]}" for k in ("bodhan_tts", "bodhan_stt", "date", "decided_by")
    )
    path.write_text(f"---\n{front}\n---{body or chr(10)}", encoding="utf-8")
    return state
