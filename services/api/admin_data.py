# ruff: noqa: E501
"""Admin: what data exists, what the testers told us, and deleting by scope to start fresh.

These scopes can be deleted (each needs the admin key where one is set, and the typed word DELETE),
listed in the order they are deleted, so a table is always cleared before the one it points at:
  feedback      app, content, simulation and card-flag feedback, and the lesson taps
  observations  the simulation observations from teachers
  testers       tester profiles (nickname), their usage events and their feedback
  demo          demo sessions and their AI-read scores
  papers        every paper with its items, imports, assignments, review rows and events (a paper
                that "has a sheet entered" is freed too)
  results       the class results the phones synced: class profiles, term counts, engine cohorts,
                kept sheets (the files in the private bucket are not touched here)
  modules       improvement tracks, their modules, answers, notes review, shared check-ins
  cohorts       cohorts of one class and the two-class runs
  cohort_chat   the cohort chat: posts, the AI answers' metadata, private question threads, settings
  cohort_spaces cohort spaces, their members, mentor items and audit rows
  intervention  the per-phone "Download audio" use counts (the cached audio files stay)
and `all` deletes every scope above. Never deleted here, and the page says so (KEPT, KEPT_TABLES): the
AI audit log and the cost ledgers, the paid-read cache, the paper rules, the published content and
its approvals, schools and classes, and teacher identities and consent. `KEPT_TABLES` names every
other table, and a test fails if a new table is in neither a scope nor that list.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select

from services.api.db import (
    AiReplyDraft,
    AudioDownloadUse,
    ChatConfig,
    ChatMessage,
    ChatThread,
    ClassCohort,
    ClassTermCount,
    Cohort,
    CohortAuditRow,
    CohortMember,
    CohortSpace,
    Feedback,
    LessonTap,
    MentorItem,
    ProfileSync,
    SimObservation,
    ThreadPost,
)
from services.api.devicestore import DocConflict, DocVersion, UserDoc
from services.api.feedback import ADMIN
from services.api.profiles import SESSION
from services.cohort_chat.models import ChatTimeout, PostMeta
from services.cohort_run.models import CohortRun
from services.demo.models import DemoAiRead, DemoSession
from services.modules.models import (
    CheckinShare,
    CohortPlan,
    CohortPlanModule,
    ModuleEvent,
    ModuleFeedback,
    ModuleReview,
    Track,
    TrackModule,
)
from services.papers.models import ClassProfileRow, PaperEvent, PaperItemRow, PaperReview, PaperRow
from services.papers_hub.models import PaperAssignment, PaperImport
from services.sheets_keep.models import KeptSheet
from services.tester.models import TesterDevice, TesterEvent, TesterFeedback

router = APIRouter(prefix="/api/admin", tags=["admin"])

SCOPES: dict[str, tuple[Any, ...]] = {
    "feedback": (Feedback, LessonTap),
    "observations": (SimObservation,),
    "testers": (TesterFeedback, TesterEvent, TesterDevice),
    "demo": (DemoAiRead, DemoSession),
    "papers": (PaperItemRow, PaperReview, PaperAssignment, PaperImport, PaperEvent, PaperRow),
    "results": (UserDoc, DocVersion, DocConflict, ClassTermCount, KeptSheet, ProfileSync, ClassProfileRow, Cohort),
    "modules": (CheckinShare, ModuleReview, ModuleFeedback, ModuleEvent, TrackModule, Track, CohortPlanModule, CohortPlan),
    "cohorts": (ClassCohort, CohortRun),
    "cohort_chat": (
        PostMeta, ChatTimeout, ThreadPost, AiReplyDraft, ChatMessage, ChatThread, ChatConfig,
    ),
    "cohort_spaces": (MentorItem, CohortMember, CohortSpace, CohortAuditRow),
    "intervention": (AudioDownloadUse,),
}  # fmt: skip
# Tables no scope deletes, each with the reason; every table is in SCOPES or here (a test checks).
KEPT_TABLES = {
    "ai_calls": "the ledger the budget guard adds up",
    "speech_calls": "the speech cost ledger",
    "usage_entries": "the cost ledger",
    "usage_actions": "the cost ledger",
    "demo_read_cache": "saves a paid AI read per sheet",
    "change_log": "the record of what changed because of feedback",
    "school": "schools and classes are set up, not test data",
    "classroom": "schools and classes are set up, not test data",
    "assignment": "schools and classes are set up, not test data",
    "users": "the nicknames people signed up with (the user ids)",
    "teachers": "teacher identities and consent",
    "consents": "teacher identities and consent",
    "channel_links": "teacher identities and consent",
    "link_codes": "teacher identities and consent",
    "flow_state": "teacher identities and consent",
    "rule_version": "the paper rules, owned by a person",
    "rule_template": "the paper rules, owned by a person",
    "rule_bug": "the paper rules, owned by a person",
    "blueprint": "the paper rules, owned by a person",
    "blueprint_slot": "the paper rules, owned by a person",
    "string_pack": "the paper rules, owned by a person",
    "content_versions": "published content and its approvals",
    "content_audit": "published content and its approvals",
    "track_manifests": "published content and its approvals",
    "lesson_audio": "audio already made (making it again costs a paid speech call)",
    "review_items": "approvals a coach gave",
    "review_decisions": "approvals a coach gave",
    "teacher_flags": "approvals a coach gave",
}
KEPT = {
    "ai_audit_log": (
        "The AI audit log stays: the budget guard adds it up, so deleting it hides spend."
    ),
    "pack_audio_files": (
        "The audio files already made for the intervention content stay: "
        "making them again costs a paid speech call."
    ),
    "tables": "Schools and classes, teacher identities and consent, the paper rules, the published content and its approvals, and the cost ledgers stay.",
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
