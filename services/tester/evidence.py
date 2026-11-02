"""The numbers behind the judge's Testing evidence screen. Everything is counted from the rows that
exist: no seeded testers, no placeholders. An empty database gives zeros, nulls and empty lists.

Judge and team devices are left out of the tester counts unless asked for, and are counted apart.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.tester.models import ChangeLog, TesterDevice, TesterEvent, TesterFeedback

CHANGE_FILE = Path(__file__).resolve().parents[2] / "docs" / "YOU_SAID_WE_CHANGED.md"
ROLE_EVENTS = ("role_selected", "view_as_role")
MAIN_SCREENS_NOT = {"roles", "judge"}
DURATION_BUCKETS = ("under_10s", "10_30s", "30s_2m", "over_2m")


def _day(ts: datetime) -> str:
    return ts.date().isoformat()


def sync_change_log(db: Session, path: Path = CHANGE_FILE) -> int:
    """Load docs/YOU_SAID_WE_CHANGED.md into change_log (replace all rows). Returns the row count."""
    if not path.exists():
        return 0
    rows: list[ChangeLog] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        ref = cells[3] if len(cells) > 3 and cells[3] not in ("", "-", "—") else None
        rows.append(
            ChangeLog(
                date=cells[0], feedback_summary=cells[1], change_made=cells[2], commit_ref=ref
            )
        )
    db.query(ChangeLog).delete()
    db.add_all(rows)
    db.commit()
    return len(rows)


def purge_older_than(db: Session, now: datetime, days: int = 90) -> dict[str, int]:
    """Retention: delete events and feedback older than `days` days."""
    from datetime import timedelta

    cutoff = now - timedelta(days=days)
    n_events = db.query(TesterEvent).filter(TesterEvent.ts < cutoff).delete()
    n_feedback = db.query(TesterFeedback).filter(TesterFeedback.ts < cutoff).delete()
    db.commit()
    return {"events": n_events, "feedback": n_feedback}


def delete_device(db: Session, device_hash: str) -> dict[str, int]:
    """Delete every row held for one device hash."""
    out = {
        "events": db.query(TesterEvent).filter(TesterEvent.device_hash == device_hash).delete(),
        "feedback": db.query(TesterFeedback)
        .filter(TesterFeedback.device_hash == device_hash)
        .delete(),
        "devices": db.query(TesterDevice).filter(TesterDevice.device_hash == device_hash).delete(),
    }
    db.commit()
    return out


def evidence(db: Session, include_flagged: bool = False) -> dict[str, Any]:
    sync_change_log(db)
    devices = list(db.scalars(select(TesterDevice).where(TesterDevice.consent_stats.is_(True))))
    flagged = [d for d in devices if d.is_judge or d.is_team]
    counted = devices if include_flagged else [d for d in devices if not (d.is_judge or d.is_team)]
    keep = {d.device_hash for d in counted}
    events = [e for e in db.scalars(select(TesterEvent)) if e.device_hash in keep]
    feedback = [f for f in db.scalars(select(TesterFeedback)) if f.device_hash in keep]

    by_dev: dict[str, list[TesterEvent]] = defaultdict(list)
    for e in events:
        by_dev[e.device_hash].append(e)

    def devs_with(pred: Any) -> set[str]:
        return {e.device_hash for e in events if pred(e)}

    sessions = {e.session_id for e in events}
    returning = sum(1 for evs in by_dev.values() if len({_day(e.ts) for e in evs}) > 1)
    roles_per = [
        len({e.role for e in evs if e.type in ROLE_EVENTS and e.role}) for evs in by_dev.values()
    ]
    offline_devs = devs_with(
        lambda e: e.type == "offline_session" and bool((e.value_json or {}).get("offline"))
    )
    stamps = [e.ts for e in events] + [f.ts for f in feedback]
    ratings = [f.rating for f in feedback]

    cards = {
        "testers": len(counted),
        "sessions": len(sessions),
        "returning_testers": returning,
        "roles_tried_avg": round(sum(roles_per) / len(roles_per), 1) if roles_per else None,
        "tours_completed": sum(1 for e in events if e.type == "tour_completed"),
        "feedback_received": len(feedback),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "offline_share": round(len(offline_devs) / len(counted), 2) if counted else None,
        "date_from": _day(min(stamps)) if stamps else None,
        "date_to": _day(max(stamps)) if stamps else None,
    }

    day_sets: dict[str, set[str]] = defaultdict(set)
    for e in events:
        day_sets[_day(e.ts)].add(e.device_hash)
    funnel_role = [
        {"stage": "selected", "testers": len(devs_with(lambda e: e.type in ROLE_EVENTS))},
        {
            "stage": "screen",
            "testers": len(
                devs_with(
                    lambda e: e.type == "screen_viewed" and e.screen_id not in MAIN_SCREENS_NOT
                )
            ),
        },
        {"stage": "feature", "testers": len(devs_with(lambda e: e.type == "feature_used"))},
    ]
    step_ids = sorted(
        {e.step_id for e in events if e.type == "tour_step_viewed" and e.step_id},
        key=lambda s: (len(s), s),
    )
    funnel_tour = [
        {"stage": "started", "testers": len(devs_with(lambda e: e.type == "tour_started"))}
    ]
    funnel_tour += [
        {
            "stage": f"step_{s}",
            "testers": len(
                devs_with(lambda e, s=s: e.type == "tour_step_viewed" and e.step_id == s)
            ),
        }
        for s in step_ids
    ]
    funnel_tour += [
        {"stage": "completed", "testers": len(devs_with(lambda e: e.type == "tour_completed"))},
        {"stage": "skipped", "testers": len(devs_with(lambda e: e.type == "tour_skipped"))},
    ]

    ratings_by_dev: dict[str, list[int]] = defaultdict(list)
    for f in feedback:
        ratings_by_dev[f.device_hash].append(f.rating)
    table: list[dict[str, Any]] = []
    anon = 0
    for d in sorted(counted, key=lambda x: x.created_at):
        evs = by_dev.get(d.device_hash, [])
        listed = d.nickname_public
        if not listed:
            anon += 1
        rs = ratings_by_dev.get(d.device_hash, [])
        table.append(
            {
                "name": d.nickname if listed else f"Anonymous tester {anon:02d}",
                "listed": listed,
                "hash6": d.device_hash[:6],
                "roles_tried": len({e.role for e in evs if e.type in ROLE_EVENTS and e.role}),
                "tours_completed": sum(1 for e in evs if e.type == "tour_completed"),
                "features_used": len(
                    {e.feature_id for e in evs if e.type == "feature_used" and e.feature_id}
                ),
                "sessions": len({e.session_id for e in evs}),
                "last_seen": _day(max(e.ts for e in evs)) if evs else _day(d.last_seen_at),
                "rating": round(sum(rs) / len(rs), 1) if rs else None,
            }
        )

    def mix(attr: str) -> list[dict[str, Any]]:
        c = Counter((getattr(d, attr) or "unknown") for d in counted)
        return [
            {"label": k, "testers": v} for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    changes = db.scalars(select(ChangeLog).order_by(ChangeLog.date.desc(), ChangeLog.id.desc()))
    return {
        "include_flagged": include_flagged,
        "cards": cards,
        "testers_by_day": [{"day": k, "testers": len(v)} for k, v in sorted(day_sets.items())],
        "role_funnel": funnel_role,
        "tour_funnel": funnel_tour,
        "by_source": mix("invite_source"),
        "device_class": mix("device_class"),
        "language": mix("language"),
        "testers": table,
        "feedback": [
            {
                "rating": f.rating,
                "role": f.role,
                "screen_id": f.screen_id,
                "tags": list(f.tags or []),
                "comment": f.comment,
                "day": _day(f.ts),
            }
            for f in sorted(feedback, key=lambda x: x.ts, reverse=True)
        ],
        "changes": [
            {
                "date": c.date,
                "feedback": c.feedback_summary,
                "change": c.change_made,
                "commit": c.commit_ref,
            }
            for c in changes
        ],
        "excluded": {
            "judge_devices": sum(1 for d in flagged if d.is_judge),
            "team_devices": sum(1 for d in flagged if d.is_team),
        },
    }
