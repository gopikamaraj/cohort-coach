# ruff: noqa: E501
"""The cloud copy of a user's data: private to her, counted for the staff assigned to it, bounded."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

A, B = "ana", "ben"  # two teachers; X-User is the normalised nickname


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    engine = make_engine(f"sqlite:///{tmp_path / 's.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def h(user: str, role: str = "teacher") -> dict[str, str]:
    return {"X-User": user, "X-Role": role}


def enter(client: TestClient, user: str, class_name: str, counts: dict[str, int], n: int, code: str = "c1") -> None:
    client.put(f"/api/store/classes/{code}", json={"data": {"id": code, "name": class_name}}, headers=h(user))
    doc = {"id": f"{code}:1", "classId": code, "term": 1, "createdAt": 1, "childrenChecked": n, "counts": {}, "anyCounts": counts}
    client.put(f"/api/store/profiles/{code}:1", json={"data": doc}, headers=h(user))


def test_a_user_reads_back_what_she_wrote_and_only_her_own(client: TestClient) -> None:
    doc = {"id": "c-1:1", "children": [["1", "2"]], "status": "closed"}
    assert client.put("/api/store/checks/c-1:1", json={"data": doc}, headers=h(A)).status_code == 200
    assert client.get("/api/store", headers=h(A)).json()["checks"] == {"c-1:1": doc}
    assert client.get("/api/store", headers=h(B)).json()["checks"] == {}  # another teacher sees nothing


def test_a_write_replaces_and_a_delete_removes(client: TestClient) -> None:
    client.put("/api/store/settings/lang", json={"data": {"key": "lang", "value": "en"}}, headers=h(A))
    client.put("/api/store/settings/lang", json={"data": {"key": "lang", "value": "ta"}}, headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["settings"]["lang"]["value"] == "ta"
    client.delete("/api/store/settings/lang", headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["settings"] == {}
    client.put("/api/store/classes/c-1", json={"data": {"id": "c-1"}}, headers=h(A))
    client.delete("/api/store", headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["classes"] == {}


def test_bad_collection_and_size_are_refused(client: TestClient) -> None:
    assert client.put("/api/store/transcripts/1", json={"data": {}}, headers=h(A)).status_code == 404  # rehearsals never go
    assert client.put("/api/store/checks/ok", json={"data": "x" * 300_000}, headers=h(A)).status_code == 413
    assert client.put("/api/store/checks/bad id", json={"data": {}}, headers=h(A)).status_code in (404, 422)


def test_a_coach_sees_her_assigned_classes_added_up_and_makes_a_cohort_from_the_pool(client: TestClient) -> None:
    enter(client, "ana", "3A", {"PV-HEARD": 4}, 20)
    enter(client, "ben", "3B", {"PV-HEARD": 3, "SUB-SFL": 2}, 18)
    assert client.get("/api/store/coach-summary", headers=h("ana")).status_code == 403  # a teacher cannot
    before = client.get("/api/store/coach-summary", headers=h("cora", "coach")).json()
    assert before["classes"] == [] and before["pool"]["PV-HEARD"] == 7 and before["pool"]["_classes"] == 2  # nothing assigned: counts of all, no names
    body = {"name": "Place value group", "error": "PV-HEARD"}
    made = client.post("/api/cohorts/class-only/coach", json=body, headers=h("cora", "coach")).json()
    assert made["classes"] == 2 and made["counts"] == {"PV-HEARD": 7} and made["children_checked"] == 38 and made["scope"] == "coach"
    assert client.post("/api/cohorts/class-only/coach", json=body, headers=h("cora", "coach")).json()["id"] == made["id"]
    s = client.get("/api/store/coach-summary", headers=h("cora", "coach")).json()
    assert s["totals"] == {"classes": 2, "children_checked": 38, "children_showing": {"PV-HEARD": 7, "SUB-SFL": 2}}
    assert all(set(c) == {"teacher", "class", "errors"} for c in s["classes"])  # no class's own count
    one = {"name": "Borrowing group", "error": "SUB-SFL"}
    assert client.post("/api/cohorts/class-only/coach", json=one, headers=h("cora", "coach")).status_code == 422  # only one class shows it
    assert client.post("/api/cohorts/class-only/coach", json=body, headers=h("ana")).status_code == 403


def test_coaches_and_mentors_list_the_checks_of_their_assigned_cohorts_by_label_only(client: TestClient) -> None:
    check = {"id": "x", "kind": "pre", "status": "closed", "children": [["3", "4"], ["", ""], ["5", "6"]], "absent": [1]}
    enter(client, "ana", "3A", {"PV-HEARD": 4}, 20)
    enter(client, "ben", "3B", {"PV-HEARD": 3}, 18)
    client.put("/api/store/checks/x", json={"data": check}, headers=h("ana"))
    client.post("/api/cohorts/class-only/coach", json={"name": "G", "error": "PV-HEARD"}, headers=h("cora", "coach"))
    rows = client.get("/api/store/all/checks", headers=h("cora", "coach")).json()
    assert [r["id"] for r in rows] == ["x"] and rows[0]["data"]["entered"] == 2 and rows[0]["data"]["absent"] == 1
    assert "children" not in rows[0]["data"] and "'3'" not in str(rows)  # counts only, never answers
    assert client.get("/api/store/all/checks", headers=h("mira", "mentor")).json() == []  # not her cohort
    assert client.get("/api/store/all/checks", headers=h("ana")).status_code == 403  # a teacher cannot
    assert client.get("/api/store/all/checks", headers=h("olga", "officer")).status_code == 403
    assert client.get("/api/store/all/profiles", headers=h("cora", "coach")).status_code == 404  # results and settings are not offered


def test_the_officer_sees_the_entered_classes_as_groups_and_the_five_class_rule_holds_unless_lowered(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    for user, nick, counts, later in (("ana", "3A", {"PV-HEARD": 6}, {"PV-HEARD": 2}), ("ben", "3B", {"PV-HEARD": 5}, {"PV-HEARD": 3})):
        client.put("/api/store/classes/c1", json={"data": {"id": "c1", "name": nick}}, headers=h(user))
        client.put("/api/store/profiles/p1", json={"data": {"id": "p1", "classId": "c1", "term": 1, "createdAt": 1, "childrenChecked": 20, "counts": {}, "anyCounts": counts}}, headers=h(user))
        client.put("/api/store/profiles/p2", json={"data": {"id": "p2", "classId": "c1", "term": 2, "createdAt": 2, "childrenChecked": 20, "counts": {}, "anyCounts": later}}, headers=h(user))
    o = client.get("/api/officer/entered", headers=h("olga", "officer")).json()
    assert o["min_classes"] == 2  # the pilot default
    monkeypatch.setenv("OFFICER_MIN_CLASSES", "5")  # block scale: the five-class rule
    o = client.get("/api/officer/entered", headers=h("olga", "officer")).json()
    assert o["min_classes"] == 5 and all(c["hidden"] for c in o["error_map"]["cells"])  # two classes: hidden by the rule
    assert client.get("/api/officer/entered", headers=h("ana")).status_code == 403
    monkeypatch.setenv("OFFICER_MIN_CLASSES", "2")
    o = client.get("/api/officer/entered", headers=h("olga", "officer")).json()
    pv = next(c for c in o["error_map"]["cells"] if c["error"] == "PV-HEARD")
    assert o["lowered"] and pv["classes"] == 2 and pv["showing"] == 2 and pv["children_showing"] == 5 and pv["children_checked"] == 40
    row = o["results"]["rows"][0]
    assert (row["error"], row["before"], row["after"], row["fall_points"]) == ("PV-HEARD", 11, 5, 15.0)
    assert o["funnel"]["wip"]


def test_the_officer_counts_a_mistake_seen_even_once_and_ignores_the_confirmed_count(client: TestClient) -> None:
    for user, n in (("ana", 3), ("ben", 2)):
        enter(client, user, "c", {"SUB-SFL": n}, 20)
    s = client.get("/api/store/coach-summary", headers=h("olga", "officer")).json()
    assert s["totals"]["children_showing"] == {"SUB-SFL": 5} and all(c["errors"] == ["SUB-SFL"] for c in s["classes"])


def test_the_officer_can_make_a_cohort_and_sees_no_class_or_teacher_name(client: TestClient) -> None:
    for user, nick in (("ana", "3A"), ("ben", "3B")):
        enter(client, user, nick, {"SUB-SFL": 4}, 20)
    s = client.get("/api/store/coach-summary", headers=h("olga", "officer")).json()
    assert all(set(c) == {"errors"} for c in s["classes"])
    made = client.post("/api/cohorts/class-only/officer", json={"name": "Borrowing group", "error": "SUB-SFL"}, headers=h("olga", "officer"))
    assert made.status_code == 200 and made.json()["classes"] == 2
    assert len(client.get("/api/cohorts/class-only/officer", headers=h("olga", "officer")).json()) == 1
    assert client.post("/api/cohorts/class-only/officer", json={"name": "x", "error": "SUB-SFL"}, headers=h("cora", "coach")).status_code == 403


def test_the_officer_button_forms_cohorts_and_each_teacher_gets_her_own_copy(client: TestClient) -> None:
    for user, counts in (("ana", {"SUB-SFL": 1}), ("ben", {"SUB-SFL": 2, "PV-HEARD": 1}), ("cia", {})):
        enter(client, user, "c", counts, 20)
    assert client.post("/api/cohorts/class-only/form", headers=h("ana")).status_code == 403
    out = client.post("/api/cohorts/class-only/form", headers=h("olga", "officer")).json()
    assert [c["errors"] for c in out["created"]] == [["SUB-SFL"]] and out["created"][0]["classes"] == 2  # PV-HEARD: one class only
    again = client.post("/api/cohorts/class-only/form", headers=h("olga", "officer")).json()
    assert again["created"] == [] and again["already"] == 1
    mine_a = client.get("/api/cohorts/class-only", headers=h("ana")).json()
    assert len(mine_a) == 1 and mine_a[0]["check_id"] == "c1:1" and mine_a[0]["classes"] == 2 and mine_a[0]["scope"] == "member"
    assert len(client.get("/api/cohorts/class-only", headers=h("ben")).json()) == 1
    assert client.get("/api/cohorts/class-only", headers=h("cia")).json() == []  # her class shows no mistake: not in it
    assert len(client.get("/api/cohorts/class-only", headers=h("ana")).json()) == 1  # a second visit adds nothing
