# ruff: noqa: E501
"""Identity (the nickname is the user id) and access (who may call which route).

Marked `no_autoregister`: these tests sign people up themselves and also check what happens when no one is
signed in, which the suite-wide default user would hide."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api import access
from services.api.db import Base, make_engine
from services.api.identity import check_nickname, normalise
from services.api.main import create_app
from services.api.profiles import get_session

pytestmark = pytest.mark.no_autoregister

ANA, BEN, CORA, MIRA, OLGA = "ana", "ben", "cora", "mira", "olga"  # two teachers, a coach, a mentor, an officer
STAFF_ROLE = {CORA: "coach", MIRA: "mentor", OLGA: "officer"}


@pytest.fixture
def app_and_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, TestClient]]:
    monkeypatch.setenv("JUDGE_MODE", "1")  # staff roles exist only in the judge deployment
    engine = make_engine(f"sqlite:///{tmp_path / 'a.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield app, TestClient(app)


@pytest.fixture
def client(app_and_client: tuple[Any, TestClient]) -> TestClient:
    return app_and_client[1]


def sign_up(client: TestClient, *names: str) -> None:
    for n in names:
        assert client.post("/api/users/register", json={"nickname": n}).status_code == 201


def who(name: str) -> dict[str, str]:
    role = STAFF_ROLE.get(name, "teacher")
    return {"X-User": name, "X-Role": role}


# ---------------------------------------------------------------- the nickname is the user id


def test_a_nickname_is_normalised_and_unique(client: TestClient) -> None:
    assert normalise("  Ana   María ") == "ana maría"
    first = client.post("/api/users/register", json={"nickname": "Priya Devi"})
    assert first.status_code == 201 and first.json() == {"id": "priya devi", "nickname": "Priya Devi"}
    again = client.post("/api/users/register", json={"nickname": "  PRIYA   devi"})  # the same normalised id
    assert again.status_code == 409 and again.json()["detail"]["code"] == "taken"
    assert "taken" in again.json()["detail"]["message"]


def test_sign_in_is_by_nickname_and_needs_no_password(client: TestClient) -> None:
    sign_up(client, "Ravi")
    ok = client.post("/api/users/signin", json={"nickname": "ravi"})
    assert ok.status_code == 200 and ok.json()["id"] == "ravi"
    assert client.post("/api/users/signin", json={"nickname": "nobody"}).status_code == 404
    assert client.get("/api/users/me", headers={"X-User": "ravi"}).json()["id"] == "ravi"
    assert client.get("/api/users/me", headers={"X-User": "ghost"}).status_code == 401  # an unregistered name is no one


def test_a_nickname_is_checked(client: TestClient) -> None:
    for bad, code in (("ab", "length"), ("x" * 31, "length"), ("no/slash", "characters"), ("Coach", "reserved"), ("unclaimed", "reserved")):
        res = client.post("/api/users/register", json={"nickname": bad})
        assert res.status_code == 422 and res.json()["detail"]["code"] == code, bad
    assert check_nickname("தமிழ் ஆசிரியர்") == "தமிழ் ஆசிரியர்"  # Tamil and Hindi nicknames are fine
    # a non-Latin nickname travels URL-encoded in the header
    sign_up(client, "தமிழ் ஆசிரியர்")
    from urllib.parse import quote

    assert client.get("/api/users/me", headers={"X-User": quote("தமிழ் ஆசிரியர்")}).status_code == 200


# ---------------------------------------------------------------- every route has a rule


def routes(app: Any) -> list[tuple[str, str]]:
    spec = app.openapi()["paths"]
    return [(m.upper(), p) for p, ops in spec.items() for m in ops]


def concrete(path: str) -> str:
    import re

    return re.sub(r"\{[^}]+\}", "x1", path)


def test_every_route_has_an_access_rule_and_every_rule_is_used(app_and_client: tuple[Any, TestClient]) -> None:
    app, _ = app_and_client
    missing = [(m, p) for m, p in routes(app) if p.startswith("/api/") and access.rule_for(m, concrete(p)) is None]
    assert missing == [], f"routes with no access rule: {missing}"
    unused = [r.pattern.pattern for r in access.RULES if not any(r.matches(m, concrete(p)) for m, p in routes(app))]
    # the tester routes exist only when TESTER_STATS is on
    assert [u for u in unused if "tester" not in u and "testing" not in u] == [], f"rules that match no route: {unused}"


def test_a_route_with_no_rule_is_closed_not_open(client: TestClient) -> None:
    assert access.rule_for("GET", "/api/something/new") is None
    app = client.app
    seen = {"hit": False}

    @app.get("/api/something/new")  # type: ignore[attr-defined]
    def _new() -> dict[str, bool]:
        seen["hit"] = True
        return {"ok": True}

    res = client.get("/api/something/new", headers=who(ANA))
    assert res.status_code == 403 and not seen["hit"]


def test_the_gate_for_every_route_and_every_caller(app_and_client: tuple[Any, TestClient]) -> None:
    """Anonymous, two teachers, a coach, a mentor and an officer call every route with an empty request. The gate
    alone decides 401 / 403 / 404 here; past the gate the handler may say anything else (usually 422 for the
    empty body), and the object-level tests below check what the handler returns."""
    app, client = app_and_client
    sign_up(client, ANA, BEN, CORA, MIRA, OLGA)
    checked = 0
    for method, path in routes(app):
        if not path.startswith("/api/"):
            continue
        rule = access.rule_for(method, concrete(path))
        assert rule is not None
        url = concrete(path)
        anon = client.request(method, url)
        if rule.who in ("public", "external", "admin"):
            assert anon.status_code != 401 or rule.who == "admin", (method, path)
        else:
            assert anon.status_code == 401, (method, path, anon.status_code)  # not signed in: always refused
        for name in (ANA, BEN, CORA, MIRA, OLGA):
            res = client.request(method, url, headers=who(name))
            if rule.who == "staff":
                allowed = rule.roles or access.STAFF
                role = STAFF_ROLE.get(name, "teacher")
                if role not in allowed:
                    assert res.status_code == 403, (method, path, name, res.status_code)
                else:
                    assert res.status_code not in (401,), (method, path, name, res.text)
            elif rule.who in ("user", "judge"):
                assert res.status_code != 401, (method, path, name, res.text)
        checked += 1
    assert checked >= 200


def test_staff_roles_are_refused_outside_the_judge_deployment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUDGE_MODE", raising=False)
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    c = TestClient(app)
    sign_up(c, CORA)
    res = c.get("/api/store/coach-summary", headers={"X-User": CORA, "X-Role": "coach"})
    assert res.status_code == 403  # a production session cannot take a staff role by sending a header
    assert c.get("/api/demo/block", headers={"X-User": CORA}).status_code == 404  # the judge demo is not there


# ---------------------------------------------------------------- one user's data is not another's


def class_doc(c: TestClient, who_: str, code: str, name: str) -> None:
    assert c.put(f"/api/store/classes/{code}", json={"data": {"id": code, "name": name}}, headers=who(who_)).status_code == 200


def result(c: TestClient, who_: str, code: str, anyc: dict[str, int], n: int = 20) -> None:
    doc = {"id": f"{code}:1", "classId": code, "term": 1, "createdAt": 1, "childrenChecked": n, "counts": {}, "anyCounts": anyc}
    assert c.put(f"/api/store/profiles/{code}:1", json={"data": doc}, headers=who(who_)).status_code == 200


def test_two_teachers_have_separate_stores_even_for_the_same_class_code(client: TestClient) -> None:
    sign_up(client, ANA, BEN)
    class_doc(client, ANA, "c-0000000001", "Ana's 3A")
    class_doc(client, BEN, "c-0000000001", "Ben's 3A")  # the same code: a class is its owner plus its code
    assert client.get("/api/store", headers=who(ANA)).json()["classes"]["c-0000000001"]["name"] == "Ana's 3A"
    assert client.get("/api/store", headers=who(BEN)).json()["classes"]["c-0000000001"]["name"] == "Ben's 3A"
    client.delete("/api/store/classes/c-0000000001", headers=who(BEN))
    assert client.get("/api/store", headers=who(ANA)).json()["classes"]["c-0000000001"]["name"] == "Ana's 3A"  # Ben's delete is his own
    client.delete("/api/store", headers=who(BEN))
    assert "c-0000000001" in client.get("/api/store", headers=who(ANA)).json()["classes"]


def test_no_route_lists_other_teachers(client: TestClient) -> None:
    sign_up(client, ANA, BEN)
    result(client, ANA, "c-0000000001", {"SUB-SFL": 4})
    assert client.get("/api/store/peers?errors=SUB-SFL", headers=who(BEN)).status_code in (404, 405)  # removed
    assert client.get("/api/store/all/profiles", headers=who(CORA)).status_code in (401, 403, 404)


def test_a_teacher_cannot_read_a_class_programme_kept_sheets_or_results_of_another(client: TestClient) -> None:
    sign_up(client, ANA, BEN)
    class_doc(client, ANA, "c-0000000001", "Ana's 3A")
    assert client.get("/api/programme/c-0000000001", headers=who(ANA)).status_code == 200
    assert client.get("/api/programme/c-0000000001", headers=who(BEN)).status_code == 403
    mine = {**who(ANA), "X-Class-Id": "c-0000000001"}
    theirs = {**who(BEN), "X-Class-Id": "c-0000000001"}
    assert client.get("/api/sheet-keep/c-0000000001:1", headers=mine).status_code == 200
    assert client.get("/api/sheet-keep/c-0000000001:1", headers=theirs).status_code == 403  # not Ben's class
    body = {"term": "T1", "form": "A", "children_checked": 5, "counts": {}, "anchor_wrong_count": 0}
    assert client.post("/api/classes/c-0000000001/profile", json=body, headers=who(ANA)).status_code == 200
    assert client.delete("/api/classes/c-0000000001", headers=who(BEN)).json() == {"deleted": 0}  # his delete touches nothing of hers
    assert client.delete("/api/classes/c-0000000001", headers=who(ANA)).json() == {"deleted": 1}


def test_a_practice_session_belongs_to_the_user_who_started_it(client: TestClient, sink: Any) -> None:
    from ai.client import CallContext
    from services.api import practice as api
    from services.practice.stub_client import StubClient

    sign_up(client, ANA, BEN)
    client.app.dependency_overrides[api.get_ai_context] = lambda: CallContext(mode="stub", sink=sink, client=StubClient())  # type: ignore[attr-defined]
    made = client.post("/api/practice/sessions", json={"scenario": "SUB-SFL", "language": "en", "seed": 5}, headers=who(ANA))
    assert made.status_code == 200, made.text
    sid = made.json()["session_id"]
    assert client.get(f"/api/practice/sessions/{sid}/hints", headers=who(BEN)).status_code == 404  # looks like no session
    assert client.post(f"/api/practice/sessions/{sid}/end", headers=who(BEN)).status_code == 404
    assert client.get(f"/api/practice/sessions/{sid}/hints", headers=who(ANA)).status_code == 200


# ---------------------------------------------------------------- coaches, mentors and the officer see counts of what is theirs


def two_classes_showing(client: TestClient) -> None:
    sign_up(client, ANA, BEN, CORA, MIRA, OLGA)
    class_doc(client, ANA, "c-0000000001", "Ana's 3A")
    class_doc(client, BEN, "c-0000000002", "Ben's 3B")
    result(client, ANA, "c-0000000001", {"SUB-SFL": 6})
    result(client, BEN, "c-0000000002", {"SUB-SFL": 3})


def test_a_teacher_cannot_use_the_staff_summaries(client: TestClient) -> None:
    two_classes_showing(client)
    for path in ("/api/store/coach-summary", "/api/store/all/checks", "/api/officer/entered", "/api/cohorts/class-only/coach", "/api/cohorts/class-only/officer"):
        assert client.get(path, headers=who(ANA)).status_code == 403, path


def test_a_coach_sees_only_the_classes_of_cohorts_assigned_to_her(client: TestClient) -> None:
    two_classes_showing(client)
    cora_before = client.get("/api/store/coach-summary", headers=who(CORA)).json()
    assert cora_before["classes"] == [] and cora_before["totals"]["classes"] == 0  # nothing assigned yet
    assert cora_before["pool"]["SUB-SFL"] == 9 and cora_before["pool"]["_classes"] == 2  # a count across all classes, nothing named
    made = client.post("/api/cohorts/class-only/coach", json={"name": "Borrowing group", "error": "SUB-SFL"}, headers=who(CORA))
    assert made.status_code == 200 and made.json()["classes"] == 2
    cora = client.get("/api/store/coach-summary", headers=who(CORA)).json()
    assert sorted(c["teacher"] for c in cora["classes"]) == ["ana", "ben"] and cora["totals"]["classes"] == 2
    # a mentor not assigned to it sees none of it; another coach (here: the officer's cohort list) is separate
    mira = client.get("/api/store/coach-summary", headers=who(MIRA)).json()
    assert mira["classes"] == [] and mira["totals"]["classes"] == 0
    assert client.get("/api/store/all/checks", headers=who(MIRA)).json() == []
    assert [r["name"] for r in client.get("/api/cohorts/class-only/coach", headers=who(CORA)).json()] == ["Borrowing group"]
    # in the judge demo any user may act as a coach, but a coach sees only the cohorts she made herself
    assert client.get("/api/cohorts/class-only/coach", headers={**who(CORA), "X-User": "mira"}).json() == []


def test_the_officer_sees_counts_across_all_and_never_a_teacher_or_class(client: TestClient) -> None:
    two_classes_showing(client)
    s = client.get("/api/store/coach-summary", headers=who(OLGA)).json()
    assert s["totals"] == {"classes": 2, "children_checked": 40, "children_showing": {"SUB-SFL": 9}}
    assert all(set(c) == {"errors"} for c in s["classes"])
    o = client.get("/api/officer/entered", headers=who(OLGA)).json()
    cell = next(c for c in o["error_map"]["cells"] if c["error"] == "SUB-SFL")
    assert cell["showing"] == 2 and cell["children_showing"] == 9 and cell["children_checked"] == 40
    assert "ana" not in str(o) and "Ana" not in str(o) and "c-0000000001" not in str(o)
    made = client.post("/api/cohorts/class-only/officer", json={"name": "Everyone", "error": "SUB-SFL"}, headers=who(OLGA))
    assert made.status_code == 200
    # a coach does not see the officer's cohort as hers
    assert client.get("/api/cohorts/class-only/coach", headers=who(CORA)).json() == []


def test_a_teacher_gets_her_own_copy_of_a_cohort_her_class_is_in_and_only_that(client: TestClient) -> None:
    two_classes_showing(client)
    sign_up(client, "dev")
    class_doc(client, "dev", "c-0000000003", "Dev's 3C")
    result(client, "dev", "c-0000000003", {"PV-HEARD": 5})
    client.post("/api/cohorts/class-only/coach", json={"name": "Borrowing group", "error": "SUB-SFL"}, headers=who(CORA))
    assert [c["name"] for c in client.get("/api/cohorts/class-only", headers=who(ANA)).json()] == ["Borrowing group"]
    assert [c["name"] for c in client.get("/api/cohorts/class-only", headers=who(BEN)).json()] == ["Borrowing group"]
    assert client.get("/api/cohorts/class-only", headers=who("dev")).json() == []  # her class is not in it
