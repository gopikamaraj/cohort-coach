"""The screen map behind the pre-deploy check: every route is covered and every screen name is valid
(the question gaps themselves are reported by scripts/check_assistant_questions.py, not failed here)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from services.assistant.questions import VALID_SCREENS

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "caq", ROOT / "scripts" / "check_assistant_questions.py"
)
assert spec and spec.loader
caq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caq)


def test_the_check_finds_no_structural_problem() -> None:
    assert caq.check()["problems"] == []


def test_every_route_of_the_app_is_a_valid_question_screen() -> None:
    routes = caq.app_routes()
    assert "landing" in routes and "papers" in routes and "two-classes" in routes
    assert set(routes) <= set(VALID_SCREENS)


def test_the_role_picker_asks_for_landing_questions() -> None:
    app = (ROOT / "apps" / "pwa" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert 'route === "/roles" ? "landing"' in app  # not "any": it would show generic questions


def test_a_gap_is_reported_for_a_screen_with_too_few_questions() -> None:
    gaps = {(g["role"], g["screen"]) for g in caq.check()["gaps"]}
    assert all(role != "judge" or screen != "papers" for role, screen in gaps)  # judge/papers has 2
