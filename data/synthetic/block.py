"""The simulated block: 40 schools, 120 Grade 3 classes, two termly checks, planted track effects.

Everything here is SIMULATED and says so. Children exist only inside this function, as latent
error sets and answer vectors; what leaves it is exactly what production would store: class-level
counts per term, plus the engine's own track assignments, arms and cohorts. The output is a pure
function of the config and the names file (seeded), so it has a stable hash.

Counts come from running the real engine (`diagnose_child`, `class_profile`) on simulated answer
sheets, so the 2-item rule filters one-off slips here exactly as it would on real sheets.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import yaml

from engine.bugs import answer_codes, correct_answer, error_answers, probes, untracked_signatures
from engine.diagnosis import class_profile, diagnose_child
from engine.grouping import (
    Arm,
    ClassRecord,
    assign_tracks,
    form_cohorts,
    split_waitlist,
)
from engine.items import generate_form
from engine.model import ErrorCode, Form, Item, ItemType

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).with_name("config.yaml")
NAMES_PATH = ROOT / "content" / "personas" / "teachers_simulated.yaml"
LABEL = (
    "SIMULATED DATA: a fictional block built for demonstration. No real school, teacher or child."
)

H, R, N = ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE, ErrorCode.ADD_NOCARRY
SFL, NODEC = ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC
WHOLE = "ADD-WHOLE-ONES"
# Errors that cannot sit together in one child: a child writes a number one way or the other.
FAMILIES: tuple[tuple[ErrorCode, ...], ...] = ((H, R), (N,), (SFL, NODEC))

Latent = frozenset[str]  # error codes (as strings) plus WHOLE


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        loaded: dict[str, Any] = yaml.safe_load(f)
    return loaded


def load_names(path: Path = NAMES_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        loaded: dict[str, Any] = yaml.safe_load(f)
    return loaded


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(data: Any) -> str:
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    keys = sorted(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


# --- children (latent, never leave this module) ------------------------------------------


def _class_prevalence(
    rng: random.Random, dominant: str, medium: str, cfg: dict[str, Any]
) -> dict[str, float]:
    dom, bg = cfg["dominant_p"], cfg["background_p"]
    p: dict[str, float] = {}
    for code in ErrorCode:
        if code is R and medium != "hindi" and dominant != R.value:
            p[code.value] = 0.0  # reversal is a Hindi-order effect; keep it out elsewhere
        elif code.value == dominant:
            p[code.value] = _clip(rng.gauss(dom["mean"], dom["sd"]), dom["min"], dom["max"])
        else:
            p[code.value] = _clip(rng.gauss(bg["mean"], bg["sd"]), 0.0, bg["max"])
    return p


def _draw_child(rng: random.Random, p: dict[str, float], whole_p: float) -> Latent:
    out: set[str] = set()
    u = rng.random()
    if u < p[H.value]:
        out.add(H.value)
    elif u < p[H.value] + p[R.value]:
        out.add(R.value)
    if rng.random() < p[N.value]:
        out.add(N.value)
    u = rng.random()
    if u < p[SFL.value]:
        out.add(SFL.value)
    elif u < p[SFL.value] + p[NODEC.value]:
        out.add(NODEC.value)
    if rng.random() < whole_p:
        out.add(WHOLE)
    return frozenset(out)


def _evolve(rng: random.Random, latent: Latent, fix: dict[str, float], onset: float) -> Latent:
    kept = {e for e in sorted(latent) if rng.random() >= fix.get(e, 0.0)}
    for family in FAMILIES:
        if not any(e.value in latent for e in family) and rng.random() < onset:
            kept.add(rng.choice(family).value)
    return frozenset(kept)


def _slip(rng: random.Random, item: Item, share: float) -> int:
    recognised = sorted(answer_codes(item))
    correct = correct_answer(item)
    if recognised and rng.random() < share:
        return rng.choice(recognised)
    high = 999 if item.type is ItemType.DICTATION else 99
    while True:
        value = rng.randint(1, high)
        if value != correct and value not in recognised:
            return value


def _answer(rng: random.Random, item: Item, errors: Latent, child_cfg: dict[str, Any]) -> int:
    relevant = [e for e in probes(item) if e.value in errors]
    if relevant and rng.random() < child_cfg["error_answer_rate"]:
        pool = sorted(error_answers(item).get(rng.choice(relevant), frozenset()))
        if pool:
            return rng.choice(pool)
    if WHOLE in errors and item.type is ItemType.ADD_CARRY:
        if rng.random() < child_cfg["whole_ones_rate"]:
            whole = sorted(untracked_signatures(item).get(WHOLE, frozenset()))
            if whole:
                return whole[0]
    if rng.random() < child_cfg["slip_rate"]:
        return _slip(rng, item, child_cfg["slip_recognised_share"])
    return correct_answer(item)


def _check_class(
    rng: random.Random,
    form: Form,
    latents: list[Latent],
    attendance: float,
    child_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Run one class's check: simulate sheets, diagnose with the engine, keep only the counts."""
    kids = []
    for errors in latents:
        if rng.random() >= attendance:
            continue
        readings = [_answer(rng, item, errors, child_cfg) for item in form.items]
        kids.append(diagnose_child(form, readings))
    profile = class_profile(kids)
    return {
        "children_checked": profile.children_checked,
        "counts": {c.value: n for c, n in profile.counts.items()},
        "anchor_wrong_count": profile.anchor_wrong_count,
        "untracked": dict(sorted(profile.untracked.items())),
    }


# --- the block ---------------------------------------------------------------------------


def _merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    merged.update(override or {})
    return merged


def generate_block(
    overrides: dict[str, Any] | None = None, names: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the whole simulated block. `overrides` replaces top-level config keys (tests)."""
    cfg = _merge(load_config(), overrides)
    names = names or load_names()
    seed = cfg["seed"]
    rng = random.Random(f"{seed}|structure")

    # Schools: medium mix and type from the config; each school has three Grade 3 sections.
    media = [m for m, n in sorted(cfg["schools_per_medium"].items()) for _ in range(n)]
    if len(media) != cfg["n_schools"]:
        raise ValueError("schools_per_medium must add up to n_schools")
    rng.shuffle(media)
    schools = [
        {
            "school_id": f"S{i + 1:02d}",
            "name": f"Simulated school {i + 1:02d}",
            "school_type": _weighted(rng, cfg["school_type_weights"]),
            "medium": media[i],
            "simulated": True,
        }
        for i in range(cfg["n_schools"])
    ]

    # Teachers: fictional, first name plus an initial, alternating gender so the split is exact.
    n_classes = cfg["n_schools"] * cfg["classes_per_school"]
    pools = {
        g: rng.sample([(f, i) for f in names[g] for i in names["initials"]], (n_classes + 1) // 2)
        for g in ("female", "male")
    }
    classes: list[dict[str, Any]] = []
    for s_idx, school in enumerate(schools):
        for k in range(cfg["classes_per_school"]):
            n = s_idx * cfg["classes_per_school"] + k
            first, initial = pools["female" if n % 2 == 0 else "male"][n // 2]
            classes.append(
                {
                    "class_id": f"C{n + 1:03d}",
                    "school_id": school["school_id"],
                    "teacher_id": f"T{n + 1:03d}",
                    "teacher_name": f"{first} {initial}.",
                    "section": "ABCDEFGH"[k],
                    "medium": school["medium"],
                    "simulated": True,
                }
            )

    # Children (latent) and the first check.
    form1 = generate_form(cfg["forms"]["t1_seed"])
    form2 = generate_form(cfg["forms"]["t2_seed"], like=form1)
    latents: dict[str, list[Latent]] = {}
    t1: dict[str, dict[str, Any]] = {}
    for c in classes:
        crng = random.Random(f"{seed}|class|{c['class_id']}|init")
        dominant = _weighted(crng, cfg["dominant_weights"][c["medium"]])
        p = _class_prevalence(crng, dominant, c["medium"], cfg)
        size = crng.randint(cfg["class_size"]["min"], cfg["class_size"]["max"])
        latents[c["class_id"]] = [_draw_child(crng, p, cfg["whole_ones_p"]) for _ in range(size)]
        t1[c["class_id"]] = _check_class(
            random.Random(f"{seed}|class|{c['class_id']}|T1"),
            form1,
            latents[c["class_id"]],
            cfg["attendance"],
            cfg["child"],
        )

    # The engine groups classes from their counts, exactly as it will on the server.
    school_of = {s["school_id"]: s for s in schools}
    records = [
        _record(c, school_of[c["school_id"]], cfg["grade"], cfg["block_id"], t1[c["class_id"]])
        for c in classes
    ]
    tracks = assign_tracks(records)
    entries = split_waitlist(tracks, seed=cfg["split_seed"])
    plan = form_cohorts(entries, Arm.THIS_TERM, seed=cfg["cohort_seed"])
    arm_of = {e.assignment.class_id: e for e in entries}

    # Between the checks: natural drift for everyone, plus the planted effect where trained.
    tc = cfg["term_change"]
    t2: dict[str, dict[str, Any]] = {}
    for c in classes:
        cid = c["class_id"]
        fix = {e.value: tc["natural_fix"] for e in ErrorCode} | {WHOLE: tc["natural_fix"]}
        entry = arm_of.get(cid)
        if entry is not None and entry.arm is Arm.THIS_TERM:
            error = entry.assignment.error.value
            fix[error] = min(1.0, fix[error] + tc["tracks"][error]["extra_fix"])
        erng = random.Random(f"{seed}|class|{cid}|evolve")
        latents[cid] = [_evolve(erng, child, fix, tc["onset"]) for child in latents[cid]]
        t2[cid] = _check_class(
            random.Random(f"{seed}|class|{cid}|T2"),
            form2,
            latents[cid],
            cfg["attendance"],
            cfg["child"],
        )

    out: dict[str, Any] = {
        "simulated": True,
        "label": LABEL,
        "seed": seed,
        "config_hash": _hash(cfg),
        "block_id": cfg["block_id"],
        "grade": cfg["grade"],
        "schools": schools,
        "classes": classes,
        "terms": {
            "T1": {"form_label": form1.label, "classes": t1},
            "T2": {"form_label": form2.label, "classes": t2},
        },
        "assignments": [
            {
                "class_id": e.assignment.class_id,
                "track": e.assignment.error.value,
                "version": tc["tracks"][e.assignment.error.value]["version"],
                "arm": e.arm.value,
                "stratum": e.stratum,
                "reason": e.assignment.reason,
                "children_checked": e.assignment.children_checked,
                "children_showing": e.assignment.children_showing,
            }
            for e in entries
        ],
        "cohorts": [
            {
                "cohort_id": co.cohort_id,
                "error": co.error.value,
                "medium": co.medium,
                "size": len(co.class_ids),
                "class_ids": list(co.class_ids),
                "block_id": co.block_id,
                "cross_block": co.cross_block,
                "undersized": co.undersized,
                "mentor_slot": co.mentor_slot,
            }
            for co in plan.cohorts
        ],
        "unplaced": [{"class_id": cid, "why": why} for cid, why in plan.unplaced],
    }
    out["data_hash"] = _hash(out)
    return out


def _record(
    c: dict[str, Any], school: dict[str, Any], grade: int, block_id: str, term: dict[str, Any]
) -> ClassRecord:
    return ClassRecord(
        class_id=c["class_id"],
        school_id=c["school_id"],
        block_id=block_id,
        school_type=school["school_type"],
        grade=grade,
        medium=c["medium"],
        children_checked=term["children_checked"],
        counts={ErrorCode(k): v for k, v in term["counts"].items()},
    )


def class_records(block: dict[str, Any], term: str) -> list[ClassRecord]:
    """The engine's view of one term of a generated (or loaded) block: counts only."""
    school_of = {s["school_id"]: s for s in block["schools"]}
    data = block["terms"][term]["classes"]
    return [
        _record(
            c, school_of[c["school_id"]], block["grade"], block["block_id"], data[c["class_id"]]
        )
        for c in block["classes"]
    ]
