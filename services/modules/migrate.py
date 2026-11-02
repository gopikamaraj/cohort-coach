# ruff: noqa: E501
"""One-time, repeatable changes to rows made before a rename. Safe to run on every start.

`tried_to_worked`: the answer "tried" became "worked" (2 Nov 2026). Rows made earlier hold the old word in
`module_feedback.answer`, `track_modules.branch`, the reason code and event details; they are rewritten.
On Postgres the answer column is also widened to fit "not_tried" (create_all does not alter a table).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from services.modules.models import ModuleEvent, ModuleFeedback, TrackModule


def widen_answer_column(engine: Engine) -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE module_feedback ALTER COLUMN answer TYPE VARCHAR(10)"))


def widen_profile_form(engine: Engine) -> None:
    """A check's form is now a paper id (P-…), longer than the old letter; Postgres enforces the length."""
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE profile_sync ALTER COLUMN form TYPE VARCHAR(40)"))


def tried_to_worked(db: Session) -> int:
    """Returns how many rows changed (0 on a second run)."""
    changed = 0
    for fb in db.query(ModuleFeedback).filter(ModuleFeedback.answer == "tried"):
        fb.answer = "worked"
        changed += 1
    for m in db.query(TrackModule):
        if m.branch == "tried":
            m.branch = "worked"
            changed += 1
        if isinstance(m.reason, dict) and m.reason.get("code") == "tried":
            m.reason = {**m.reason, "code": "worked"}
            changed += 1
    for e in db.query(ModuleEvent):
        d = e.detail if isinstance(e.detail, dict) else {}
        fix = {
            k: ("worked" if v == "tried" else v)
            for k, v in d.items()
            if k in ("answer", "branch", "reason")
        }
        if any(d.get(k) != v for k, v in fix.items()):
            e.detail = {**d, **fix}
            changed += 1
    if changed:
        db.commit()
    return changed
