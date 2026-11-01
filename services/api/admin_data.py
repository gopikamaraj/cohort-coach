"""Admin: what data exists, what the testers told us, and deleting by scope to start fresh.

Four scopes can be deleted (each needs the admin key where one is set, and the typed word DELETE):
  feedback      app, content, simulation and card-flag feedback
  observations  the simulation observations from teachers
  testers       tester profiles (nickname), their usage events and their feedback
  demo          demo sessions and their AI-read scores
and `all` deletes those four. Two things are never deleted here, and the page says so:
  * the AI audit log: it is the ledger the budget guard adds up, so clearing it would hide spend;
  * the demo's paid-read cache: it saves a paid AI read per sheet, so clearing it costs money.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select

from services.api.db import Feedback, SimObservation
from services.api.feedback import ADMIN
from services.api.profiles import SESSION
from services.demo.models import DemoAiRead, DemoSession
from services.tester.models import TesterDevice, TesterEvent, TesterFeedback

router = APIRouter(prefix="/api/admin", tags=["admin"])

SCOPES: dict[str, tuple[Any, ...]] = {
    "feedback": (Feedback,),
    "observations": (SimObservation,),
    "testers": (TesterFeedback, TesterEvent, TesterDevice),
    "demo": (DemoAiRead, DemoSession),
}
KEPT = {
    "ai_audit_log": (
        "The AI audit log stays: the budget guard adds it up, so deleting it hides spend."
    ),
    "demo_read_cache": (
        "The demo's paid-read cache stays: clearing it would cost a paid AI read per sheet."
    ),
}


def _count(db: Any, model: Any) -> int:
    return int(db.execute(select(func.count()).select_from(model)).scalar_one())


@router.get("/data")
def admin_data(db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "scopes": {
            name: {
                "rows": sum(_count(db, m) for m in models),
                "tables": [m.__tablename__ for m in models],
            }
            for name, models in SCOPES.items()
        },
        "kept": KEPT,
    }


@router.get("/testers")
def admin_testers(db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """The testers' own inputs: counts, and their feedback with no device id or nickname."""
    rows = db.execute(
        select(TesterFeedback).order_by(TesterFeedback.id.desc()).limit(200)
    ).scalars()
    return {
        "devices": _count(db, TesterDevice),
        "events": _count(db, TesterEvent),
        "feedback": [
            {
                "rating": r.rating, "tags": list(r.tags or []), "comment": r.comment,
                "role": r.role, "screen": r.screen_id, "at": r.ts.isoformat(),
            }
            for r in rows
        ],
    }  # fmt: skip


class DeleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: Literal["DELETE"]


@router.delete("/data/{scope}")
def admin_delete(scope: str, body: DeleteIn, db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    names = list(SCOPES) if scope == "all" else [scope]
    if scope != "all" and scope not in SCOPES:
        raise HTTPException(404, "No such data scope.")
    deleted: dict[str, int] = {}
    for name in names:
        n = 0
        for model in SCOPES[name]:
            n += db.execute(delete(model)).rowcount or 0
        deleted[name] = n
    db.commit()
    return {"deleted": deleted, "kept": KEPT}
