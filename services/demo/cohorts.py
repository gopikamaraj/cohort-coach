"""The other classes and the cohorts, for the demo. SIMULATED classes, real cohort code.

The other classes come from the simulated block generator (data/synthetic/block.py), class-level
counts only. Her class joins them with the counts her phone sent. Then the real engine runs: one
track per class (PV-HEARD first, else the highest share, engine/grouping.py assign_tracks), the
seeded waitlist split (this term or next), and cohort formation. A mentor is suggested by the
same-term candidate rule (engine/mentors.py check_candidate). Every line of explanation is built
from these facts by code.
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from typing import Any

from data.synthetic.block import class_records, generate_block
from engine.diagnosis import profile_from_counts
from engine.grouping import Arm, ClassRecord, assign_tracks, form_cohorts, split_waitlist
from engine.mentors import check_candidate
from engine.model import ErrorCode

YOU = "DEMO-YOU"
MIN_CELL = 5  # the officer view hides any figure covering fewer than 5 classes


@cache
def _block(n_schools: int, per_school: int, seed: int, weights_key: str) -> dict[str, Any]:
    weights = dict(item.split("=") for item in weights_key.split(","))
    w = {k: float(v) for k, v in weights.items()}
    return generate_block(
        {
            "seed": seed,
            "n_schools": n_schools,
            "classes_per_school": per_school,
            "schools_per_medium": {"english": n_schools},
            "dominant_weights": {"english": w, "hindi": w, "tamil": w},
        }
    )


def other_classes(scenario: dict[str, Any]) -> list[ClassRecord]:
    oc = scenario["other_classes"]
    key = ",".join(f"{k}={v}" for k, v in sorted(oc["dominant_weights"].items()))
    block = _block(int(oc["schools"]), int(oc["classes_per_school"]), int(oc["seed"]), key)
    return class_records(block, "T1")


def her_record(scenario: dict[str, Any], counts: dict[str, int], checked: int) -> ClassRecord:
    return ClassRecord(
        class_id=YOU,
        school_id="S-DEMO",
        block_id="B1",
        school_type="government",
        grade=int(scenario["grade"]),
        medium=str(scenario["medium"]),
        children_checked=checked,
        counts={code: int(counts.get(code.value, 0)) for code in ErrorCode},
    )


def plan(scenario: dict[str, Any], counts: dict[str, int], checked: int) -> dict[str, Any]:
    """Cohorts this term for the simulated classes and hers, with the facts behind each line."""
    others = other_classes(scenario)
    mine = her_record(scenario, counts, checked)
    records = [*others, mine]
    assignments = assign_tracks(records)
    entries = split_waitlist(assignments, int(scenario["split_seed"]))
    cohorts = form_cohorts(entries, Arm.THIS_TERM, int(scenario["split_seed"])).cohorts
    by_class = {e.assignment.class_id: e for e in entries}
    her_profile = profile_from_counts(checked, mine.counts)
    her_entry = by_class.get(YOU)
    block_showing: Counter[ErrorCode] = Counter()
    block_checked = 0
    for r in records:
        block_checked += r.children_checked
        for code, n in r.counts.items():
            block_showing[code] += n
    out = []
    for c in sorted(cohorts, key=lambda c: c.error.value):
        mentor = _mentor(
            others,
            c.error,
            int(scenario["grade"]),
            str(scenario["medium"]),
            block_showing[c.error],
            block_checked,
        )
        includes_you = YOU in c.class_ids
        you_eligible = c.error in her_profile.eligible
        out.append(
            {
                "id": c.cohort_id,
                "error": c.error.value,
                "classes": len(c.class_ids),
                "simulated_classes": len([i for i in c.class_ids if i != YOU]),
                "undersized": c.undersized,
                "includes_you": includes_you,
                "you_eligible": you_eligible,
                "you_next_term": you_eligible and not includes_you,
                "mentor": mentor,
            }
        )
    tracks = Counter(a.error.value for a in assignments)
    return {
        "simulated": True,
        "other_classes": len(others),
        "schools": len({r.school_id for r in others}),
        "cohorts": out,
        "you": {
            "checked": checked,
            "counts": {k.value: v for k, v in mine.counts.items()},
            "eligible": [e.value for e in her_profile.eligible],
            "track": her_profile.track.value if her_profile.track else None,
            "arm": her_entry.arm.value if her_entry else None,
            "reason": (her_entry.assignment.reason if her_entry else None),
        },
        "tracks": dict(tracks),
        "this_term": sum(1 for e in entries if e.arm is Arm.THIS_TERM),
        "next_term": sum(1 for e in entries if e.arm is Arm.NEXT_TERM),
        "no_track": len(records) - len(assignments),
    }


def _mentor(
    others: list[ClassRecord],
    error: ErrorCode,
    grade: int,
    medium: str,
    block_showing: int,
    block_checked: int,
) -> dict[str, Any] | None:
    """The same-term candidate with the fewest children showing the error, if any meets the rule."""
    best: tuple[int, ClassRecord] | None = None
    for r in others:
        showing = int(r.counts.get(error, 0))
        ok = check_candidate(
            grade=r.grade,
            medium=r.medium,
            children_showing=showing,
            children_checked=r.children_checked,
            block_children_showing=block_showing,
            block_children_checked=block_checked,
            cohort_grade=grade,
            cohort_medium=medium,
            consent=True,  # simulated classes: consent is assumed for the demo
        )
        if ok.qualifies and (best is None or showing < best[0]):
            best = (showing, r)
    if best is None:
        return None
    showing, r = best
    return {
        "class": f"Simulated class {r.class_id}",
        "showing": showing,
        "checked": r.children_checked,
        "kind": "candidate",
    }


def dashboard(p: dict[str, Any]) -> dict[str, Any]:
    """The officer's view of the demo block: classes per cohort, shares of classes by tracked error,
    tracks started, approvals pending is added by the API. Any cell under 5 classes is hidden."""
    total = p["other_classes"] + 1
    rows = []
    for c in p["cohorts"]:
        n = c["classes"]
        rows.append({"error": c["error"], "classes": n if n >= MIN_CELL else None})
    by_error = []
    for code, n in sorted(p["tracks"].items()):
        by_error.append(
            {
                "error": code,
                "classes": n if n >= MIN_CELL else None,
                "share": round(100 * n / total) if n >= MIN_CELL else None,
            }
        )
    return {
        "simulated": True,
        "classes": total,
        "cohorts": rows,
        "by_error": by_error,
        "tracks_started": p["this_term"] if p["this_term"] >= MIN_CELL else None,
        "waiting_next_term": p["next_term"] if p["next_term"] >= MIN_CELL else None,
        "min_cell": MIN_CELL,
    }


def before_after(
    scenario: dict[str, Any], counts: dict[str, int], checked: int, her_post: Any
) -> list[dict[str, Any]]:
    """Children showing each cohort's error at the first check and the next, summed over the
    cohort's classes: the simulated block's two terms, and her class's simulated post-test.
    A cohort of fewer than 5 classes is hidden. Simulated."""
    oc = scenario["other_classes"]
    key = ",".join(f"{k}={v}" for k, v in sorted(oc["dominant_weights"].items()))
    block = _block(int(oc["schools"]), int(oc["classes_per_school"]), int(oc["seed"]), key)
    t1 = {r.class_id: r for r in class_records(block, "T1")}
    t2 = {r.class_id: r for r in class_records(block, "T2")}
    mine = her_record(scenario, counts, checked)
    t1[YOU] = mine
    t2[YOU] = ClassRecord(
        **{
            **mine.__dict__,
            "children_checked": her_post.children_checked,
            "counts": dict(her_post.counts),
        }
    )
    entries = split_waitlist(assign_tracks(list(t1.values())), int(scenario["split_seed"]))
    out = []
    for c in sorted(
        form_cohorts(entries, Arm.THIS_TERM, int(scenario["split_seed"])).cohorts,
        key=lambda c: c.error.value,
    ):
        n = len(c.class_ids)
        before = sum(int(t1[i].counts.get(c.error, 0)) for i in c.class_ids)
        after = sum(int(t2[i].counts.get(c.error, 0)) for i in c.class_ids)
        checked_before = sum(t1[i].children_checked for i in c.class_ids)
        checked_after = sum(t2[i].children_checked for i in c.class_ids)
        shown = n >= MIN_CELL
        out.append(
            {
                "error": c.error.value,
                "classes": n if shown else None,
                "before": before if shown else None,
                "checked_before": checked_before if shown else None,
                "after": after if shown else None,
                "checked_after": checked_after if shown else None,
            }
        )
    return out
