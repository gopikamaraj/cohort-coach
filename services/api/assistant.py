"""The assistant's HTTP surface. The scope is decided here, on the server, and nowhere else.

* The authenticated role is "judge" in the judge-mode deployment (JUDGE_MODE=1, set by the server,
  never by a request) and "teacher" everywhere else, where `require("assistant.ask")` and the role
  header rules allow nothing more. "View as" is refused for anyone but the judge session.
* The About this product tab (surface "about") is always the judge scope.
* Nothing here writes: the assistant approves, sends and deletes nothing, and no route accepts an
  action. What is logged is the effective role, the scope name and the question id; never the
  question text or who asked.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ai.config import judge_mode
from services.api.ratelimit import RateLimiter, client_ip
from services.api.roles import require
from services.assistant import answer, limits, retrieve
from services.assistant.scopes import ROLES, Scope, ScopeError, ViewAsRefused, scope_for

limiter = RateLimiter("assistant", 30)
router = APIRouter(
    prefix="/api/assistant",
    tags=["assistant"],
    dependencies=[Depends(require("assistant.ask")), Depends(limiter)],
)

LANGS = ("en", "hi", "ta")
SOURCES_LINE = {
    "judge": "the repository documents, the rubric map, the deck and the video script",
    "teacher": "the approved help pages",
    "mentor": "the mentor help pages",
    "coach": "the review and coach help pages",
    "officer": "the programme help pages",
}


def authenticated_role() -> str:
    """Who is really asking. Decided by the deployment, never by the request."""
    return "judge" if judge_mode() else "teacher"


def resolve(authenticated: str, view_as: str | None, surface: str) -> Scope:
    try:
        return scope_for(authenticated, view_as or None, surface)
    except ViewAsRefused as e:
        raise HTTPException(403, "View as is available to the judge session only.") from e
    except ScopeError as e:
        raise HTTPException(400, "Unknown role or surface.") from e


def session_key(request: Request, device: str | None) -> str:
    raw = device or client_ip(request)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def lang_of(lang: str) -> str:
    return lang if lang in LANGS else "en"


class AskBody(BaseModel):
    question_id: str | None = Field(default=None, max_length=12)
    text: str | None = Field(default=None, max_length=answer.MAX_QUESTION_CHARS)
    lang: str = "en"
    view_as: str | None = Field(default=None, max_length=12)
    surface: Literal["main", "about"] = "main"


@router.get("/scope")
def get_scope(
    view_as: str | None = Query(default=None, max_length=12),
    surface: Literal["main", "about"] = "main",
    lang: str = "en",
    who: str = Depends(authenticated_role),
) -> dict[str, Any]:
    scope = resolve(who, view_as, surface)
    lib = answer.library()
    lg = answer._lang(scope, lang_of(lang))
    sha = answer.commit_sha(lib)
    from services.assistant.tools import tools_for

    return {
        "role": scope.role,
        "title": scope.heading(lg),
        "can": scope.line("can", lg),
        "cannot": scope.line("cannot", lg),
        "answers_from": SOURCES_LINE[scope.role],
        "namespaces": list(scope.namespaces),
        "tools": [{"name": t.name, "status": t.status, "what": t.what} for t in tools_for(scope)],
        "min_count": scope.min_count,
        "commit": sha,
        "provisional": bool(lib.submission.get("provisional", True)),
        "can_view_as": who == "judge",
        "view_as_roles": [r for r in ROLES if r != "judge"] if who == "judge" else [],
        "language": lg,
    }


@router.get("/questions")
def get_questions(
    view_as: str | None = Query(default=None, max_length=12),
    surface: Literal["main", "about"] = "main",
    screen: str = Query(default="any", max_length=16),
    step: int | None = Query(default=None, ge=1, le=20),
    lang: str = "en",
    who: str = Depends(authenticated_role),
) -> dict[str, Any]:
    scope = resolve(who, view_as, surface)
    return {"role": scope.role, "questions": answer.suggested(scope, screen, step, lang_of(lang))}


@router.get("/answer/{question_id}")
def get_answer(
    question_id: str,
    view_as: str | None = Query(default=None, max_length=12),
    surface: Literal["main", "about"] = "main",
    lang: str = "en",
    who: str = Depends(authenticated_role),
) -> dict[str, Any]:
    """The pre-written answer to a suggested question. A GET so the app can keep it for offline use."""
    scope = resolve(who, view_as, surface)
    return answer.ask(scope, question_id=question_id, lang=lang_of(lang)).to_dict()


@router.post("/ask")
def ask(
    body: AskBody,
    request: Request,
    who: str = Depends(authenticated_role),
    x_device_id: str | None = Header(default=None, max_length=64),
) -> dict[str, Any]:
    scope = resolve(who, body.view_as, body.surface)
    a = answer.ask(
        scope,
        question_id=body.question_id,
        text=body.text,
        lang=lang_of(body.lang),
        session=session_key(request, x_device_id),
        caps=limits.CAPS,
    )
    return a.to_dict()


@router.get("/path")
def test_path(who: str = Depends(authenticated_role)) -> dict[str, Any]:
    """The judge's ten-minute test path: steps with the route, a sample input and the matching questions."""
    if who != "judge":
        raise HTTPException(403, "The test path is for the judge session.")
    return answer.library().path or {"steps": []}


@router.get("/usage")
def usage(who: str = Depends(authenticated_role)) -> dict[str, Any]:
    """Today's model use by role: calls, tokens and cost. Counts only, for the judge session."""
    if who != "judge":
        raise HTTPException(403, "Usage is for the judge session.")
    return {"today": limits.CAPS.snapshot()}


def reload_index() -> None:  # used by tests after they rebuild the bundled index
    answer.reload()
    retrieve.reload()
