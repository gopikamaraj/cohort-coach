"""Who may see what: the assistant's scope for each role, read from assistant_scopes.yaml.

The scope comes from the authenticated role. Only a judge session may "view as" another role, and
the judge's About tab always uses the judge scope. Nothing the user types can widen a scope: the
retrieval function takes its namespaces from a Scope object and from nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCOPES_FILE = ROOT / "assistant_scopes.yaml"
BUNDLED_SCOPES = Path(__file__).with_name("index") / "assistant_scopes.yaml"
ROLES = ("teacher", "mentor", "coach", "officer", "judge")
LANGS = ("en", "hi", "ta")


class ScopeError(Exception):
    """A request named a role or surface that does not exist."""


class ViewAsRefused(ScopeError):
    """Only an authenticated judge may view as another role."""


@dataclass(frozen=True)
class Scope:
    role: str
    title: dict[str, str]
    answers_in: str  # "own": the user's language; "en": English
    namespaces: tuple[str, ...]
    data_tools: tuple[str, ...]
    question_bank: str
    actions: tuple[str, ...]
    can: dict[str, str]
    cannot: dict[str, str]
    min_count: int

    def line(self, which: str, lang: str) -> str:
        text = self.can if which == "can" else self.cannot
        return text.get(lang) or text["en"]

    def heading(self, lang: str) -> str:
        return self.title.get(lang) or self.title["en"]


def _check(data: dict[str, Any]) -> None:
    roles = data["roles"]
    if tuple(roles) != ROLES:
        raise ScopeError(f"assistant_scopes.yaml must define exactly {ROLES}, in that order")
    known = set(data["namespaces"])
    owners: dict[str, list[str]] = {}
    for role, spec in roles.items():
        if spec["actions"]:
            raise ScopeError(f"{role}: the assistant is read-only; actions must be empty")
        if not set(spec["namespaces"]) <= known:
            raise ScopeError(f"{role}: unknown namespace {set(spec['namespaces']) - known}")
        for lang in ("en",):
            if not spec["can"].get(lang) or not spec["cannot"].get(lang):
                raise ScopeError(f"{role}: the {lang} can and cannot lines are required")
        for ns in spec["namespaces"]:
            owners.setdefault(ns, []).append(role)
    if roles["judge"]["data_tools"]:
        raise ScopeError("judge: no user data, so no data tools")
    # Namespaces never cross: only the shared ones listed here may belong to two roles.
    shared = {"product_help": {"teacher", "judge"}, "teacher_kb": {"teacher", "mentor"}}
    for ns, who in owners.items():
        if len(who) > 1 and set(who) != shared.get(ns):
            raise ScopeError(f"namespace {ns} is held by {who}; namespaces must not cross")
    if int(data["min_count"]) < 5:
        raise ScopeError("min_count must be at least 5")


def load_scopes(path: Path = SCOPES_FILE) -> dict[str, Scope]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _check(data)
    out: dict[str, Scope] = {}
    for role, s in data["roles"].items():
        out[role] = Scope(
            role=role,
            title=dict(s["title"]),
            answers_in=s["answers_in"],
            namespaces=tuple(s["namespaces"]),
            data_tools=tuple(s["data_tools"]),
            question_bank=s["question_bank"],
            actions=tuple(s["actions"]),
            can=dict(s["can"]),
            cannot=dict(s["cannot"]),
            min_count=int(data["min_count"]),
        )
    return out


@cache
def scopes() -> dict[str, Scope]:
    """The repository's file when it is there (development), else the copy bundled with the index
    (the API image holds services/ only)."""
    return load_scopes(SCOPES_FILE if SCOPES_FILE.exists() else BUNDLED_SCOPES)


def effective_role(authenticated: str, view_as: str | None = None) -> str:
    """The role whose scope applies: the view-as role if set (judges only), else the real one."""
    if authenticated not in ROLES:
        raise ScopeError("unknown role")
    if not view_as:
        return authenticated
    if authenticated != "judge":
        raise ViewAsRefused("view as is available to a judge session only")
    if view_as not in ROLES:
        raise ScopeError("unknown role to view as")
    return view_as


def scope_for(authenticated: str, view_as: str | None = None, surface: str = "main") -> Scope:
    """The scope for a request. The About tab (surface "about") is always the judge scope."""
    if surface not in ("main", "about"):
        raise ScopeError("unknown surface")
    if surface == "about":
        if authenticated != "judge":
            raise ViewAsRefused("the About tab is for the judge session")
        return scopes()["judge"]
    return scopes()[effective_role(authenticated, view_as)]
