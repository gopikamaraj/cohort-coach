"""Cohort formation for a handful of classes, with the reason each class is in or out.

Pure code over class counts. There is one cohort per mistake (decided 4 Nov 2026, DECISIONS.md): a class
joins the cohort of every tracked mistake it shows by the engine's rule (at least 1 child showing it and at
least 10 children checked; the 25% share line was removed on 2 Nov), so one cohort holds every class that
shows that mistake, and a class that shows two mistakes is in two cohorts. What each teacher gets next in a
cohort still follows her own feedback (`next_lesson`). Classes with the same mistake, grade and medium form
a cohort once there are `min_classes` of them; until then they wait. A class's own focus (PV-HEARD first,
else the highest count) is still reported, for her results card; it no longer decides her cohort.
At pilot scale (fewer classes than the engine's cohort size) there is no waitlist split: the pilot
compares the trained error with the untrained ones instead (CLAUDE.md section 5, pilot verdict).

Every reason is returned as a code and the facts behind it; the screen words it in the teacher's
language. No sentence is written here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from engine.diagnosis import MIN_CHILDREN_CHECKED, TRACKED, profile_from_counts
from engine.mentors import check_candidate
from engine.model import ErrorCode
from services.cohort_run.scenario import ClassCounts
from services.cohort_run.settings import SINGLE_ITEM_LABEL, CohortSettings, cohort_label


def used_counts(c: ClassCounts, settings: CohortSettings) -> dict[str, int]:
    """The counts the rule uses: the 2-item counts, plus the single-question ones when allowed.
    A child is in at most one of the two for an error, so the sum never passes children checked."""
    out = {code.value: int(c.counts.get(code.value, 0)) for code in ErrorCode}
    if settings.allow_single_item_probes:
        for k, v in c.possible.items():
            out[k] = min(c.children_checked, out.get(k, 0) + int(v))
    return out


def _track(c: ClassCounts, settings: CohortSettings) -> tuple[ErrorCode | None, str | None, Any]:
    """The class's own focus (for her results card) and the engine's profile, whose `eligible` mistakes are
    the cohorts the class joins."""
    used = used_counts(c, settings)
    profile = profile_from_counts(c.children_checked, {ErrorCode(k): v for k, v in used.items()})
    if profile.track is None:
        return None, None, profile
    reason = "pv_heard_first" if profile.track is ErrorCode.PV_HEARD else "highest_p"
    return profile.track, reason, profile


def _joins(profile: Any) -> list[ErrorCode]:
    """The cohorts a class joins: every tracked mistake it is eligible for, one cohort each."""
    return [code for code in profile.eligible if code in TRACKED]


def _class_reason(
    c: ClassCounts,
    code: ErrorCode,
    settings: CohortSettings,
    track: ErrorCode | None,
    track_reason: str | None,
    profile: Any,
) -> dict[str, Any]:
    used = used_counts(c, settings)[code.value]
    single = int(c.possible.get(code.value, 0)) if settings.allow_single_item_probes else 0
    facts: dict[str, Any] = {
        "showing": used,
        "checked": c.children_checked,
        "single": single,
        "ignored_single": 0
        if settings.allow_single_item_probes
        else int(c.possible.get(code.value, 0)),
    }
    if code not in TRACKED:
        return {"in": False, "code": "no_track_yet", **facts}
    if code in _joins(profile):  # one cohort per mistake: she is in this one whatever her class's focus is
        return {"in": True, "code": "in", "focus": code is track, **facts}
    if c.children_checked < MIN_CHILDREN_CHECKED:
        return {
            "in": False,
            "code": "too_few_checked",
            "min_checked": MIN_CHILDREN_CHECKED,
            **facts,
        }
    return {"in": False, "code": "under_line", **facts}


def _mentor(
    error: ErrorCode,
    members: list[ClassCounts],
    others: list[ClassCounts],
    settings: CohortSettings,
) -> dict[str, Any]:
    all_classes = members + others
    block_showing = sum(used_counts(c, settings)[error.value] for c in all_classes)
    block_checked = sum(c.children_checked for c in all_classes)
    grade, medium = members[0].grade, members[0].medium
    best: tuple[int, ClassCounts] | None = None
    for c in others:
        showing = used_counts(c, settings)[error.value]
        ok = check_candidate(
            grade=c.grade,
            medium=c.medium,
            children_showing=showing,
            children_checked=c.children_checked,
            block_children_showing=block_showing,
            block_children_checked=block_checked,
            cohort_grade=grade,
            cohort_medium=medium,
            consent=True,
        )
        if ok.qualifies and (best is None or showing < best[0]):
            best = (showing, c)
    if best is None:
        reason = "no_other_class" if not others else "none_did_better"
        return {"suggested": False, "reason": reason, "classes_compared": len(others)}
    return {
        "suggested": True,
        "class": best[1].code,
        "teacher": best[1].teacher,
        "kind": "candidate",
    }


def form(classes: list[ClassCounts], settings: CohortSettings) -> dict[str, Any]:
    """Who is in which cohort, who waits, and why, from the classes' counts."""
    tracks: dict[str, tuple[ErrorCode | None, str | None, Any]] = {
        c.code: _track(c, settings) for c in classes
    }
    groups: dict[tuple[str, int, str], list[ClassCounts]] = defaultdict(list)
    for c in classes:
        for code in _joins(tracks[c.code][2]):  # one cohort per mistake, with every class that shows it
            groups[(code.value, c.grade, c.medium)].append(c)
    cohorts: list[dict[str, Any]] = []
    waiting: list[dict[str, Any]] = []
    for (code, grade, medium), members in sorted(groups.items()):
        members = sorted(members, key=lambda c: c.code)
        entry = {
            "error": code,
            "grade": grade,
            "medium": medium,
            "classes": [c.code for c in members],
            "teachers": [c.teacher for c in members],
            "min_classes": settings.min_classes,
        }
        if len(members) >= settings.min_classes:
            error = ErrorCode(code)
            uses_single = settings.allow_single_item_probes and any(
                c.possible.get(code, 0) for c in members
            )
            labels = [x for x in (cohort_label(len(members), settings),) if x]
            if uses_single:
                labels.append(SINGLE_ITEM_LABEL)
            others = [c for c in classes if c not in members]
            cohorts.append(
                {
                    **entry,
                    "id": f"{code}-g{grade}-{medium}",
                    "labels": labels,
                    "showing": sum(used_counts(c, settings)[code] for c in members),
                    "checked": sum(c.children_checked for c in members),
                    "waitlist": "none_at_pilot_scale" if settings.pilot_scale else "split",
                    "mentor": _mentor(error, members, others, settings),
                }
            )
        else:
            waiting.append({**entry, "have": len(members)})
    shown = sorted(
        {k for c in classes for k, v in used_counts(c, settings).items() if v}
        | {k for c in classes for k, v in c.possible.items() if v},
        key=lambda k: list(ErrorCode).index(ErrorCode(k)),
    )
    per_class = []
    for c in classes:
        t, why, profile = tracks[c.code]
        per_class.append(
            {
                "code": c.code,
                "teacher": c.teacher,
                "checked": c.children_checked,
                "source": c.source,
                "track": t.value if t else None,
                "track_reason": why,
                "cohort": next((k["id"] for k in cohorts if c.code in k["classes"]), None),
                "cohorts": [k["id"] for k in cohorts if c.code in k["classes"]],
                "waiting": any(c.code in w["classes"] for w in waiting),
                "errors": {
                    k: _class_reason(c, ErrorCode(k), settings, t, why, profile) for k in shown
                },
            }
        )
    if cohorts:
        status = "formed"
    elif waiting:
        status = "waiting_for_classes"
    else:
        status = "no_cohort"
    return {
        "status": status,
        "settings": {
            "min_classes": settings.min_classes,
            "allow_single_item_probes": settings.allow_single_item_probes,
            "source": settings.source,
            "pilot_scale": settings.pilot_scale,
        },
        "cohorts": cohorts,
        "waiting": waiting,
        "classes": per_class,
    }
