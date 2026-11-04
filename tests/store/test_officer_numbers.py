# ruff: noqa: E501
"""The officer's numbers come from the answers (engine), a before-and-after reads anchor items of a pre-test and its
twin only, Create a cohort shows classes as anonymous labels, and the demo switches every minimum off."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from engine.bugs import correct_answer, error_answers
from engine.forms import FORM_A, FORM_B
from engine.model import ErrorCode, Form
from services.api import caps
from services.api.db import Base, CohortAuditRow, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

OFFICER = {"X-User": "olga", "X-Role": "officer"}


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
    c = TestClient(app)
    c.factory = factory  # type: ignore[attr-defined]
    yield c


def h(user: str) -> dict[str, str]:
    return {"X-User": user, "X-Role": "teacher"}


def child(form: Form, code: ErrorCode | None, hits: int) -> list[str]:
    """One child's ten answers: right everywhere, except `hits` items that probe `code`, answered the way that error does."""
    row, left = [], hits
    for item in form.items:
        wrong = sorted(error_answers(item).get(code, frozenset())) if code else []
        if code and left > 0 and wrong:
            row.append(str(wrong[0]))
            left -= 1
        else:
            row.append(str(correct_answer(item)))
    return row


def enter(client: TestClient, user: str, form: Form, kind: str, rows: list[list[str]], at: int, class_id: str = "c1", cid: str | None = None) -> None:
    cid = cid or f"{class_id}:{at}"
    client.put(f"/api/store/classes/{class_id}", json={"data": {"id": class_id, "name": f"{user}'s class"}}, headers=h(user))
    client.put(f"/api/store/checks/{cid}", json={"data": {"id": cid, "classId": class_id, "kind": kind, "children": rows, "absent": [], "updatedAt": at}}, headers=h(user))
    # what the phone saved is deliberately wrong: the server must not trust it
    client.put(f"/api/store/profiles/{cid}", json={"data": {"id": cid, "classId": class_id, "createdAt": at, "formKey": "A" if form is FORM_A else "B", "childrenChecked": 99, "counts": {"SUB-SFL": 99}, "anyCounts": {"SUB-SFL": 99}}}, headers=h(user))


def test_numbers_come_from_the_answers_not_from_what_the_phone_saved(client: TestClient) -> None:
    rows = [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, ErrorCode.SUB_SFL, 2), child(FORM_A, ErrorCode.SUB_SFL, 1), child(FORM_A, None, 0)]
    enter(client, "zorro", FORM_A, "pre", rows, 1)
    for rule, want in ((2, 2), (1, 3)):  # two children show it on two or more items, three made it at least once
        s = client.get(f"/api/store/coach-summary?min_hits={rule}", headers=OFFICER).json()
        assert s["totals"]["children_checked"] == 4  # not the phone's 99
        assert s["totals"]["children_showing"].get("SUB-SFL") == want


def test_a_before_and_after_reads_a_pre_test_and_its_twin_on_anchor_items_and_lists_the_pairs_it_skips(client: TestClient) -> None:
    before = [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, None, 0)]
    after = [child(FORM_B, ErrorCode.SUB_SFL, 3), child(FORM_B, None, 0), child(FORM_B, None, 0)]
    enter(client, "zorro", FORM_A, "pre", before, 1, cid="c1:1")
    enter(client, "zorro", FORM_B, "post", after, 2, cid="c1:2")  # Form B is Form A's twin
    enter(client, "yuki", FORM_A, "pre", before, 1, cid="c1:1")
    enter(client, "yuki", FORM_A, "post", before, 2, cid="c1:2")  # a post-test on the pre-test's own paper: not a twin
    enter(client, "xena", FORM_A, "pre", before, 1, cid="c1:1")
    enter(client, "xena", FORM_B, "pre", after, 2, cid="c1:2")  # two pre-tests: not a pre/post pair
    out = client.get("/api/officer/entered?min_hits=2", headers=OFFICER).json()["results"]
    assert out["classes"] == 1 and "anchor items only" in out["basis"]
    row = next(r for r in out["rows"] if r["error"] == "SUB-SFL")
    assert (row["before"], row["before_of"], row["after"], row["after_of"]) == (2, 3, 1, 3)
    assert sorted(s["reason"] for s in out["skipped"]) == ["its first and latest checks are not a pre-test followed by a post-test", "the post-test paper is not the twin of the pre-test paper"]
    text = json.dumps(out)
    assert all(name not in text for name in ("zorro", "yuki", "xena"))  # the skipped pairs are listed by anonymous label only
    assert {s["label"] for s in out["skipped"]} <= {"Class A", "Class B", "Class C"}


def test_create_a_cohort_lists_classes_by_anonymous_label_and_the_cohort_leaves_an_audit_row(client: TestClient) -> None:
    for user in ("zorro", "yuki", "xena"):
        enter(client, user, FORM_A, "pre", [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, None, 0)], 1)
    got = client.get("/api/cohorts/class-only/officer/candidates?error=SUB-SFL&min_hits=2", headers=OFFICER).json()
    assert [c["label"] for c in got["classes"]] == ["Class A", "Class B", "Class C"] and all(c["children"] == 2 for c in got["classes"])
    assert all(set(c) == {"ref", "label", "children", "children_checked"} for c in got["classes"])
    text = json.dumps(got)
    assert all(name not in text for name in ("zorro", "yuki", "xena", "c1"))  # no nickname, no class code
    refs = [c["ref"] for c in got["classes"]]
    body = {"name": "Borrowing group", "error": "SUB-SFL", "min_hits": 2, "class_refs": refs[:2]}
    made = client.post("/api/cohorts/class-only/officer", json=body, headers=OFFICER).json()
    assert made["classes"] == 2 and made["counts"] == {"SUB-SFL": 4} and made["rule"] == {"min_hits": 2}
    assert client.post("/api/cohorts/class-only/officer", json=body, headers=OFFICER).json()["id"] == made["id"]  # the same classes, the same cohort
    other = client.post("/api/cohorts/class-only/officer", json={**body, "name": "The third", "class_refs": refs[2:]}, headers=OFFICER).json()
    assert other["id"] != made["id"]  # a different set of classes is a different cohort
    assert client.post("/api/cohorts/class-only/officer", json={**body, "class_refs": ["nonsense"]}, headers=OFFICER).status_code == 422
    with client.factory() as db:  # type: ignore[attr-defined]
        rows = list(db.scalars(select(CohortAuditRow).where(CohortAuditRow.cohort_id == made["id"])))
    assert [(r.action, r.role, r.detail["classes"], r.detail["min_hits"]) for r in rows] == [("group_created", "officer", 2, 2)]
    assert client.get("/api/cohorts/class-only/officer/candidates?error=SUB-SFL", headers=h("zorro")).status_code == 403


def test_a_member_finds_the_cohort_she_is_in_and_a_class_not_chosen_does_not(client: TestClient) -> None:
    for user in ("zorro", "yuki"):
        enter(client, user, FORM_A, "pre", [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, ErrorCode.SUB_SFL, 3)], 1)
    refs = [c["ref"] for c in client.get("/api/cohorts/class-only/officer/candidates?error=SUB-SFL", headers=OFFICER).json()["classes"]]
    client.post("/api/cohorts/class-only/officer", json={"name": "G", "error": "SUB-SFL", "class_refs": refs[:1]}, headers=OFFICER)
    mine = {u: client.get("/api/cohorts/class-only", headers=h(u)).json() for u in ("zorro", "yuki")}
    assert sorted(len(v) for v in mine.values()) == [0, 1]  # exactly the one whose class was chosen


def test_production_keeps_every_minimum_and_the_demo_turns_them_all_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUDGE_MODE", raising=False)
    monkeypatch.delenv("OFFICER_MIN_CLASSES", raising=False)
    prod = caps.describe()
    assert prod == {"off": False, "label": None, "min_classes": 5, "min_children": 10, "min_cohort_classes": 2}
    monkeypatch.setenv("OFFICER_MIN_CLASSES", "7")
    assert caps.min_classes_shown() == 7  # the production value stays configurable
    monkeypatch.setenv("JUDGE_MODE", "1")
    demo = caps.describe()
    assert demo == {"off": True, "label": "Demo: no minimum group sizes", "min_classes": 1, "min_children": 1, "min_cohort_classes": 1}


def test_in_the_demo_a_single_class_makes_a_cohort_and_every_officer_view_says_the_minimums_are_off(client: TestClient) -> None:
    enter(client, "zorro", FORM_A, "pre", [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, None, 0)], 1)
    ent = client.get("/api/officer/entered", headers=OFFICER).json()
    assert ent["caps"]["off"] and ent["min_classes"] == 1 and not ent["error_map"]["cells"][0].get("hidden")
    assert client.get("/api/officer/error-map", headers=OFFICER).json()["caps"]["label"] == "Demo: no minimum group sizes"
    assert client.get("/api/officer/results", headers=OFFICER).json()["caps"]["off"]
    made = client.post("/api/cohorts/class-only/officer", json={"name": "Just one", "error": "SUB-SFL"}, headers=OFFICER)
    assert made.status_code == 200 and made.json()["classes"] == 1


def test_with_the_production_minimums_a_figure_over_too_few_classes_is_hidden_and_a_cohort_needs_two(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    enter(client, "zorro", FORM_A, "pre", [child(FORM_A, ErrorCode.SUB_SFL, 3), child(FORM_A, None, 0)], 1)
    monkeypatch.setattr(caps, "caps_off", lambda: False)  # the judge fixture lets the officer role in; the minimums are the production ones
    ent: dict[str, Any] = client.get("/api/officer/entered", headers=OFFICER).json()
    assert ent["min_classes"] == 5 and all(c["hidden"] for c in ent["error_map"]["cells"])
    assert client.post("/api/cohorts/class-only/officer", json={"name": "Just one", "error": "SUB-SFL"}, headers=OFFICER).status_code == 422
