# ruff: noqa: E501
"""Officer views: aggregates only (P12, reduced scope).

The error map, the funnel and the track results. Every figure is computed by code from class-level
counts (the engine and `data.synthetic.block`), never by a model, and every one carries its source
label. Nothing here returns a teacher id, a class id or a school: the officer sees groups, and any
group covering fewer than 5 classes or teachers is hidden. A failed track counts against the track,
not the teacher.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import cache
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from data.synthetic.block import track_verdicts
from engine.diagnosis import MIN_CHILDREN_CHECKED
from engine.evaluation import MIN_CLASSES_SHOWN
from engine.model import ErrorCode
from services.api.db import LessonTap, ReviewItem
from services.api.profiles import BLOCK_PATH, SESSION
from services.api.roles import require
from services.content.review import OPEN

router = APIRouter(prefix="/api/officer", tags=["officer"])
RESULTS = Depends(require("officer.results"))
PILOT_MIN_CLASSES = 2
SHARE_NUMERATOR, SHARE_DENOMINATOR = 1, 4  # a class "shows" an error at 1 child in 4 or more


@cache
def _block() -> dict[str, Any]:
    return json.loads(BLOCK_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _shows(counts: dict[str, int], checked: int, code: str) -> bool:
    return (
        checked >= MIN_CHILDREN_CHECKED
        and counts.get(code, 0) * SHARE_DENOMINATOR >= checked * SHARE_NUMERATOR
    )


@router.get("/error-map")
def error_map(_: str = RESULTS) -> dict[str, Any]:
    """Share of classes showing each error, by medium (grade 3). A cell over fewer than 5 classes
    is hidden. Simulated block: labelled as such."""
    block = _block()
    t1 = block["terms"]["T1"]["classes"]
    by_medium: dict[str, list[str]] = defaultdict(list)
    for c in block["classes"]:
        by_medium[c["medium"]].append(c["class_id"])
    cells = []
    for medium, ids in sorted(by_medium.items()):
        for code in (e.value for e in ErrorCode):
            n = len(ids)
            if n < MIN_CLASSES_SHOWN:
                cells.append({"medium": medium, "error": code, "hidden": True, "classes": None})
                continue
            showing = sum(_shows(t1[i]["counts"], t1[i]["children_checked"], code) for i in ids)
            cells.append(
                {
                    "medium": medium,
                    "error": code,
                    "hidden": False,
                    "classes": n,
                    "showing": showing,
                    "share_percent": round(100 * showing / n, 1),
                }
            )
    return {
        "grade": block["grade"],
        "term": "T1",
        "simulated": bool(block["simulated"]),
        "source": "system: class counts from the checks",
        "cells": cells,
    }


@router.get("/results")
def results(_: str = RESULTS) -> dict[str, Any]:
    """Track results per version, computed now by `engine.evaluation`: the change in the share of
    children showing the error for classes on the track against the waitlist group, with a 95%
    interval, the number of classes in each group and a verdict."""
    out = []
    for version, effect in sorted(track_verdicts(_block()).items()):
        hidden = effect.hidden  # either group under 5 classes: not shown
        row: dict[str, Any] = {
            "version": version,
            "verdict": effect.verdict.value,
            "reason": effect.reason,
            "confidence_note": effect.confidence_note,
            "hidden": hidden,
        }
        if not hidden:
            row.update(
                estimate_points=effect.estimate_points,
                ci_low=effect.ci_low,
                ci_high=effect.ci_high,
                n_track=effect.n_track,
                n_comparison=effect.n_comparison,
            )
        out.append(row)
    return {
        "simulated": bool(_block()["simulated"]),
        "source": "next check, counts computed by code",
        "tracks": out,
        "note": "A failed track counts against the track, not the teacher.",
    }


def _min_entered() -> int:
    """Classes needed before a figure over the entered classes is shown: 2 while this is a pilot (decided by Gopi,
    2 Nov 2026, DECISIONS.md). Block scale sets OFFICER_MIN_CLASSES=5, the rule in CLAUDE.md section 4.3."""
    try:
        return max(1, int(os.environ.get("OFFICER_MIN_CLASSES", PILOT_MIN_CLASSES)))
    except ValueError:
        return PILOT_MIN_CLASSES


@router.get("/entered")
def entered(_: str = RESULTS, db: Session = SESSION) -> dict[str, Any]:
    """The classes that really entered a check (the cloud store), added up: error map, change between two
    checks, and what of the funnel the system can count. Counts per group; no class, teacher or school."""
    from services.api.db import ClassCohort
    from services.api.devicestore import entered_summary

    floor = _min_entered()
    summary = entered_summary(db)
    classes = summary["classes"]  # each class once, by its most recent check
    codes = [e.value for e in ErrorCode]
    out: dict[str, Any] = {"min_classes": floor, "lowered": floor < MIN_CLASSES_SHOWN, "has_data": bool(classes), "source": "system: class counts from the entered checks"}
    hidden = len(classes) < floor
    cells = []
    for code in codes:
        if hidden:
            cells.append({"error": code, "hidden": True})
            continue
        showing = sum(1 for c in classes if c["_counts"].get(code, 0) > 0)  # a mistake seen even once (possible) counts
        cells.append({"error": code, "hidden": False, "classes": len(classes), "showing": showing, "share_percent": round(100 * showing / len(classes), 1), "children_showing": sum(c["_counts"].get(code, 0) for c in classes), "children_checked": sum(c["children_checked"] for c in classes)})
    out["error_map"] = {"classes": len(classes), "cells": cells}
    # Before and after: a class with two or more checks is read first check against most recent, by date saved.
    by_class: dict[str, list[dict[str, Any]]] = {}
    for c in summary["all"]:
        by_class.setdefault(c["_class"], []).append(c)
    pairs = [(min(v, key=lambda x: x["_at"]), max(v, key=lambda x: x["_at"])) for v in by_class.values() if len(v) >= 2]
    rows = []
    for code in codes:
        na, nb = sum(a["children_checked"] for a, _ in pairs), sum(b["children_checked"] for _, b in pairs)
        sa, sb = sum(a["_counts"].get(code, 0) for a, _ in pairs), sum(b["_counts"].get(code, 0) for _, b in pairs)
        if sa == 0:
            continue
        rows.append({"error": code, "before": sa, "before_of": na, "after": sb, "after_of": nb, "fall_points": round(100 * (sa / na - sb / nb), 1) if na and nb else None})
    out["results"] = {"classes": len(pairs), "rows": rows if len(pairs) >= floor else [], "hidden": bool(pairs) and len(pairs) < floor, "verdict_needs": "15 classes per arm and a comparison group, so no verdict yet"}
    cohorts = list(db.execute(select(ClassCohort).where(ClassCohort.scope == "coach")).scalars())
    out["funnel"] = {"cohorts": [{"error": c.errors[0] if c.errors else "", "classes": int(c.counts.get("_classes", 1))} for c in cohorts], "grouped_source": "system: cohorts a coach created", "wip": ["Delivered", "Tried", "Practised", "Changed"]}
    return out


def _review_waiting(db: Session) -> dict[str, Any]:
    """Content items still waiting for a human (pending, or awaiting the mentor), and how long."""
    now = datetime.now(UTC)
    ages = []
    for created in db.execute(
        select(ReviewItem.created_at).where(ReviewItem.status.in_(OPEN))
    ).scalars():
        created = created if created.tzinfo else created.replace(tzinfo=UTC)
        ages.append((now - created).days)
    return {
        "waiting": len(ages),
        "over_7_days": sum(1 for a in ages if a > 7),
        "oldest_days": max(ages) if ages else None,
        "source": "system: review queue ages; gates never auto-approve",
    }


@router.get("/funnel")
def funnel(_: str = RESULTS, db: Session = SESSION) -> dict[str, Any]:
    """Delivered, tried and how it went, per tracked error, as teacher counts with their source.
    A count under 5 teachers is hidden. Practice Class sessions are metadata only on the server and
    are not counted per cohort. Changed is the next check: "awaiting next check" until it exists."""
    taps = list(db.execute(select(LessonTap)).scalars())
    by_track: dict[str, list[LessonTap]] = defaultdict(list)
    for t in taps:
        by_track[t.track_id].append(t)
    verdicts = track_verdicts(_block())
    rows = []
    for error in (e.value for e in ErrorCode):
        mine = by_track.get(error, [])
        teachers = {t.teacher_id for t in mine}
        tried = {t.teacher_id for t in mine if t.tried}
        outcomes = Counter(t.outcome for t in mine if t.outcome)
        version = next((v for v in verdicts if v.startswith(error + " ")), None)

        def cell(n: int, source: str) -> dict[str, Any]:
            return {
                "hidden": n < MIN_CLASSES_SHOWN,
                "teachers": None if n < MIN_CLASSES_SHOWN else n,
                "source": source,
            }

        rows.append(
            {
                "error": error,
                "delivered": cell(len(teachers), "system: lessons sent"),
                "tried": cell(len(tried), "self-report: tapped Tried it in class"),
                "outcomes": None
                if len(teachers) < MIN_CLASSES_SHOWN
                else {k: outcomes.get(k, 0) for k in ("worked", "partly", "didnt")},
                "practised": {
                    "recorded": False,
                    "source": "system: not counted per cohort (sessions are metadata only)",
                },
                "changed": {
                    "status": "awaiting next check" if version is None else "see results",
                    "source": "next check, blind-scored counts",
                },
            }
        )
    return {
        "rows": rows,
        "review_waiting": _review_waiting(db),
        "median_minutes": None,
        "cap_minutes": 20,
        "rule": "fewer than 5 teachers is hidden",
    }
