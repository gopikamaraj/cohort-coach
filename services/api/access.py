# ruff: noqa: E501
"""Who may call what: one table, enforced on every request, checked against every route by a test.

Every route of the API matches exactly one rule below (a test walks the OpenAPI list and fails on any route
without one, and on any rule that matches nothing). A rule says what the CALLER must be before the handler runs:

    public     anyone (no data of anyone's: health, the role list, a signed link, sign-in itself)
    user       a signed-in user (`X-User`); the handler then limits the data to that user
    staff      a signed-in user acting as one of the named staff roles (judge deployments only)
    admin      the admin key (checked by the admin routes themselves)
    judge      a signed-in user, and the judge-mode deployment
    external   a machine caller: a webhook secret or a job token (checked by the route itself)

and `owns` says what the handler additionally enforces about the OBJECT (the ownership table, docs/privacy.md):

    self       only the caller's own records (the store, consents, practice sessions, kept sheets, tracks)
    class      a class code the caller owns (owner plus class code)
    cohort     a cohort the caller belongs to (teacher) or is assigned to (coach, mentor)
    assigned   counts for the cohorts assigned to the caller (coach, mentor); the officer sees counts of all
    counts     counts across all classes, no nickname, no class (officer)
    shared     shared by design (papers, the paper rules, approved lesson content)

A staff role is a user: the signed-in user's id is the coach's, mentor's or officer's id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from ai.config import judge_mode
from services.api.identity import optional_user
from services.api.roles import role_of

STAFF = frozenset({"coach", "mentor", "officer"})


@dataclass(frozen=True)
class Rule:
    methods: frozenset[str]
    pattern: re.Pattern[str]
    who: str  # public | user | staff | admin | judge | external
    owns: str
    roles: frozenset[str] = frozenset()

    def matches(self, method: str, path: str) -> bool:
        return (not self.methods or method in self.methods) and bool(self.pattern.fullmatch(path))


def r(who: str, owns: str, pattern: str, methods: str = "", roles: str = "") -> Rule:
    return Rule(frozenset(methods.split()), re.compile(pattern), who, owns, frozenset(roles.split()))


# Order matters: the first rule that matches wins, so specific rules come before their prefix.
RULES: list[Rule] = [
    # --- public ---
    r("public", "shared", r"/api/health"),
    r("public", "shared", r"/api/roles"),
    r("public", "shared", r"/api/users/register|/api/users/signin", "POST"),
    r("public", "shared", r"/api/flow/token/[^/]+", "GET"),  # a signed link says a language and an error, no person
    r("public", "shared", r"/api/tester/config", "GET"),
    r("external", "shared", r"/api/telegram/webhook", "POST"),
    r("external", "shared", r"/api/modules/jobs/due", "POST"),
    r("admin", "shared", r"/api/admin/.*"),
    # --- a signed-in user's own things ---
    r("user", "self", r"/api/users/me", "GET"),
    r("user", "self", r"/api/store", "GET DELETE"),
    r("user", "self", r"/api/store/[^/]+/[^/]+", "PUT DELETE"),
    r("staff", "assigned", r"/api/store/coach-summary", "GET", "coach mentor officer"),
    r("staff", "assigned", r"/api/store/all/[^/]+", "GET", "coach mentor"),
    r("user", "self", r"/api/consents", "POST"),
    r("user", "class", r"/api/classes/[^/]+(/profile)?", "POST DELETE"),
    r("user", "class", r"/api/programme/[^/]+", "GET"),
    r("user", "self", r"/api/flow/.*"),
    r("user", "self", r"/api/audio/pack(/cap|/script)?"),
    r("user", "self", r"/api/assistant/.*"),
    r("user", "self", r"/api/feedback", "POST"),
    r("user", "self", r"/api/tester/.*"),
    r("user", "counts", r"/api/judge/testing-evidence", "GET"),  # the handler wants the judge role in a judge deployment
    r("external", "counts", r"/api/team/testing-export", "GET"),  # the team token
    r("user", "self", r"/api/actions/[^/]+/usage", "GET"),
    r("user", "class", r"/api/sheet-keep/.*"),
    r("user", "self", r"/api/sheets/read", "POST"),
    r("user", "self", r"/api/stages", "POST"),
    r("user", "self", r"/api/practice/.*"),
    r("user", "shared", r"/api/lessons/audio", "GET"),
    # --- improvement plans ---
    r("staff", "assigned", r"/api/modules/coach/.*", "", "coach"),
    r("staff", "assigned", r"/api/modules/mentor/.*", "", "mentor"),
    r("user", "cohort", r"/api/modules/.*"),
    # --- cohorts and the cohort chat ---
    r("user", "cohort", r"/api/cohort-chat/.*"),
    r("user", "self", r"/api/cohorts/class-only", "GET POST"),
    r("staff", "assigned", r"/api/cohorts/class-only/coach", "GET POST", "coach"),
    r("staff", "counts", r"/api/cohorts/class-only/(officer|form)", "GET POST", "officer"),
    r("staff", "assigned", r"/api/cohorts/coach/.*", "", "coach"),
    r("staff", "assigned", r"/api/cohorts/mentor/.*", "", "mentor"),
    r("staff", "counts", r"/api/cohorts/officer/.*", "", "officer"),
    r("user", "cohort", r"/api/cohorts/.*"),
    r("staff", "counts", r"/api/officer/.*", "GET", "officer"),
    # --- papers and the rules that make them: shared by design ---
    r("user", "shared", r"/api/paper-hub/.*"),
    r("user", "shared", r"/api/papers(/.*)?"),
    r("user", "shared", r"/api/paper-rules(/.*)?"),
    # --- review queues (the coach and the programme officer are the reviewers) ---
    r("staff", "shared", r"/api/review/.*", "", "coach mentor officer"),
    # --- demo and judge mode (simulated data; JUDGE_MODE deployments only) ---
    r("judge", "self", r"/api/demo/.*"),
    r("judge", "self", r"/api/cohort-run/.*"),
    r("judge", "self", r"/api/judge/.*"),
    r("judge", "self", r"/api/pilot-data/.*"),
]

# Not API data: the interactive docs and the schema.
OPEN_PATHS = re.compile(r"/(docs|redoc|openapi\.json|docs/oauth2-redirect)")


def rule_for(method: str, path: str) -> Rule | None:
    for rule in RULES:
        if rule.matches(method.upper(), path):
            return rule
    return None


def enforce(request: Request, uid: str | None = Depends(optional_user)) -> None:
    """The one gate in front of every handler. A route with no rule is refused, never left open."""
    path = request.url.path
    if not path.startswith("/api/"):
        return
    rule = rule_for(request.method, path)
    if rule is None:
        raise HTTPException(403, "This route has no access rule, so it is closed.")
    if rule.who in ("public", "external", "admin"):
        return
    if uid is None:
        raise HTTPException(401, {"code": "sign_in", "message": "Sign in with your nickname first."})
    if rule.who == "judge" and not judge_mode():
        # /api/judge/* has always answered 403 outside judge mode; the other demo routes stay 404
        raise HTTPException(403 if path.startswith("/api/judge/") else 404, "This is part of the judge demo.")
    if rule.who == "staff":
        role = role_of(request.headers.get("x-role"))  # 403 unless a judge deployment
        if role not in (rule.roles or STAFF):
            raise HTTPException(403, "Your role cannot do this.")
