"""The scope matrix is data, and the server derives the effective role from the authenticated one."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from services.assistant.scopes import (
    ROLES,
    ScopeError,
    ViewAsRefused,
    effective_role,
    load_scopes,
    scope_for,
    scopes,
)
from services.assistant.tools import TOOLS, ToolDenied, call_tool, suppress, tools_for

ROOT = Path(__file__).resolve().parents[2]


def test_every_role_has_a_scope_with_plain_language_lines() -> None:
    assert tuple(scopes()) == ROLES
    for role, s in scopes().items():
        assert s.can["en"] and s.cannot["en"], role
        assert s.title["en"], role
        assert s.min_count >= 5


def test_the_assistant_is_read_only_in_every_scope() -> None:
    assert all(s.actions == () for s in scopes().values())


def test_namespaces_do_not_cross_except_the_two_shared_ones() -> None:
    held: dict[str, set[str]] = {}
    for role, s in scopes().items():
        for ns in s.namespaces:
            held.setdefault(ns, set()).add(role)
    shared = {"product_help": {"teacher", "judge"}, "teacher_kb": {"teacher", "mentor"}}
    for ns, who in held.items():
        if len(who) > 1:
            assert who == shared.get(ns), (ns, who)
    assert held["judge"] == {"judge"}  # the repository, deck and video script: judges only
    assert "judge" not in scopes()["teacher"].namespaces


def test_the_matrix_matches_the_design() -> None:
    s = scopes()
    assert s["teacher"].namespaces == ("teacher_kb", "product_help")
    assert s["mentor"].namespaces == ("teacher_kb", "mentor_help")
    assert s["coach"].namespaces == ("coach_kb", "coach_help")
    assert s["officer"].namespaces == ("officer_help",)
    assert s["judge"].namespaces == ("judge", "product_help")
    assert s["judge"].data_tools == ()  # a judge sees no user data


def test_view_as_is_for_a_judge_session_only() -> None:
    assert effective_role("judge", "teacher") == "teacher"
    assert effective_role("judge", None) == "judge"
    assert effective_role("teacher", None) == "teacher"
    for role in ("teacher", "mentor", "coach", "officer"):
        for target in ROLES:
            with pytest.raises(ViewAsRefused):
                effective_role(role, target)  # not even "view as myself"
    with pytest.raises(ScopeError):
        effective_role("judge", "admin")
    with pytest.raises(ScopeError):
        effective_role("admin", None)


def test_the_about_tab_is_always_the_judge_scope() -> None:
    assert scope_for("judge", "teacher", surface="about").role == "judge"
    assert (
        scope_for("judge", "teacher", surface="main").role == "teacher"
    )  # view as on the main tab
    with pytest.raises(ViewAsRefused):
        scope_for("teacher", None, surface="about")
    with pytest.raises(ScopeError):
        scope_for("judge", None, surface="settings")


def test_a_scope_file_that_widens_a_role_is_refused(tmp_path: Path) -> None:
    data = yaml.safe_load((ROOT / "assistant_scopes.yaml").read_text(encoding="utf-8"))
    bad = tmp_path / "s.yaml"
    data["roles"]["teacher"]["namespaces"].append("judge")
    bad.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ScopeError):
        load_scopes(bad)
    data = yaml.safe_load((ROOT / "assistant_scopes.yaml").read_text(encoding="utf-8"))
    data["roles"]["coach"]["actions"] = ["approve"]
    bad.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ScopeError):
        load_scopes(bad)
    data = yaml.safe_load((ROOT / "assistant_scopes.yaml").read_text(encoding="utf-8"))
    data["min_count"] = 3
    bad.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ScopeError):
        load_scopes(bad)


def test_tools_are_filtered_by_scope_and_never_cross() -> None:
    names = {r: {t.name for t in tools_for(scopes()[r])} for r in ROLES}
    assert names["judge"] == set()
    assert names["officer"] == {"cohort_counts", "block_counts", "track_verdicts"}
    assert "review_queue" not in names["officer"] and "own_class_counts" not in names["coach"]
    with pytest.raises(ToolDenied):
        call_tool(scopes()["officer"], "own_class_counts")
    with pytest.raises(ToolDenied):
        call_tool(scopes()["judge"], "cohort_counts")
    assert all(t in TOOLS for s in scopes().values() for t in s.data_tools)


def test_an_unwired_tool_says_so_instead_of_inventing_a_figure() -> None:
    out = call_tool(scopes()["officer"], "cohort_counts")
    assert out["available"] is False and "result" not in out


def test_counts_below_the_minimum_are_never_stated() -> None:
    assert suppress(4, 5) is None and suppress(5, 5) == 5 and suppress(0, 5) is None
