"""One role config: enforced by the server, shown by the dialog (addendum v3.1 section A)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.roles import ROLES, config, judge_session, require

ROOT = Path(__file__).resolve().parents[2]


def _source() -> str:
    files = [p for p in (ROOT / "services").rglob("*.py") if p.parent.name != "roles"]
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def test_every_enforced_permission_is_used_by_a_require_call_and_the_reverse() -> None:
    cfg = config()
    used = set(re.findall(r'require\("([a-z_.]+)"\)', _source()))
    enforced = {k for k, v in cfg["permissions"].items() if not v.get("planned")}
    planned = {k for k, v in cfg["permissions"].items() if v.get("planned")}
    assert used == enforced, used ^ enforced
    assert not used & planned
    on_roles = {p for r in cfg["roles"].values() for p in r["can"]}
    assert on_roles == set(cfg["permissions"])


def test_every_boundary_is_enforced_by_a_real_test_or_listed_as_planned() -> None:
    cfg = config()
    on_roles = {b for r in cfg["roles"].values() for b in r["cannot"]}
    assert on_roles == set(cfg["boundaries"])
    for bid, b in cfg["boundaries"].items():
        if b.get("planned"):
            continue
        path, _, name = b["enforced_by"].partition("::")
        assert re.search(rf"def {name}\b", (ROOT / path).read_text(encoding="utf-8")), bid


def test_every_dialog_string_exists_in_three_languages_and_has_no_percentage() -> None:
    cfg = config()
    keys: set[str] = {p["key"] for p in cfg["permissions"].values()}
    keys |= {b["key"] for b in cfg["boundaries"].values()}
    for r in cfg["roles"].values():
        keys |= {r["card"], r["holders"], r["data"]}
    for lang in ("en", "hi", "ta"):
        table = json.loads((ROOT / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
        missing = sorted(k for k in keys if not table.get(k))
        assert not missing, (lang, missing)
        if lang == "en":
            assert not [k for k in keys if "%" in table[k]]


def test_the_officer_never_gets_a_per_teacher_view() -> None:
    officer = config()["roles"]["officer"]
    assert "officer.aggregates_only" in officer["cannot"]
    assert not any("teacher" in p for p in officer["can"])


def test_weekly_caps_match_the_rules() -> None:
    caps = config()["weekly_minutes"]
    assert (caps["teacher"], caps["mentor"], caps["coach"], caps["officer"]) == (20, 30, 30, None)


# enforcement ----------------------------------------------------------------------------------


def _probe_app() -> TestClient:
    probe = FastAPI()

    @probe.get("/teacher-thing", dependencies=[Depends(require("practice.rehearse"))])
    def a() -> dict[str, bool]:
        return {"ok": True}

    @probe.get("/judge-thing", dependencies=[Depends(require("judge.inspect"))])
    def b() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(probe)


def test_default_role_is_teacher_and_may_rehearse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    c = _probe_app()
    assert c.get("/teacher-thing").status_code == 200
    assert c.get("/teacher-thing", headers={"X-Role": "teacher"}).status_code == 200


def test_a_production_session_cannot_enter_another_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    c = _probe_app()
    for role in ("officer", "coach", "mentor"):
        assert c.get("/teacher-thing", headers={"X-Role": role}).status_code == 403
    assert c.get("/teacher-thing", headers={"X-Role": "nonsense"}).status_code == 403


def test_judge_only_permissions_need_a_server_side_judge_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    c = _probe_app()
    assert c.get("/judge-thing").status_code == 403
    monkeypatch.setenv("JUDGE_MODE", "1")
    assert c.get("/judge-thing").status_code == 200


def test_a_role_without_the_permission_is_refused_even_in_judge_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "1")
    c = _probe_app()
    assert c.get("/teacher-thing", headers={"X-Role": "officer"}).status_code == 403
    assert c.get("/judge-thing", headers={"X-Role": "mentor"}).status_code == 403


def test_the_judge_flag_is_decided_by_the_server_not_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert judge_session() is False
    monkeypatch.setenv("JUDGE_MODE", "1")
    assert judge_session() is True


# the endpoint ---------------------------------------------------------------------------------


def test_get_roles_returns_the_config_the_dialog_renders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "1")
    r = TestClient(app).get("/api/roles")
    body = r.json()
    assert r.status_code == 200 and body["judge"] is True
    assert [x["id"] for x in body["roles"]] == list(ROLES)
    teacher = body["roles"][0]
    assert teacher["weekly_minutes"] == 20 and "telegram" in teacher["also_on"]
    assert all({"id", "key", "planned"} <= set(c) for c in teacher["can"])
    assert any(c["planned"] == "P11" for c in teacher["can"])  # cohort chat arrives in P11


def test_in_production_only_the_teacher_card_is_offered_without_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    body = TestClient(app).get("/api/roles").json()
    assert body["judge"] is False and [r["id"] for r in body["roles"]] == ["teacher"]
