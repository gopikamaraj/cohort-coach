"""Paper Studio over HTTP: only the coach uses the rule editor and the queue; a teacher generates
and prints approved papers; a rule change needs two people; no request carries child data."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.papers.rules import seed_rules, to_yaml

CHECK = {"id": "c-0123456789:1", "kind": "pre", "form": "A", "class_label": "3A", "term": 1}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def h(role: str, person: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    if person:
        out["X-Demo-Person"] = person
    return out


def gen(client: TestClient, language: str = "en", role: str = "teacher") -> dict:
    body = {
        "check": CHECK,
        "profile": {"source": "past", "counts": {"SUB-SFL": 9}, "checked": 18},
        "blueprint": "standard_10_5",
        "language": language,
    }
    r = client.post("/api/papers/generate", json=body, headers=h(role))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("role", ["teacher", "mentor"])
def test_teachers_and_mentors_read_the_rules_but_never_change_them(
    client: TestClient, role: str
) -> None:
    for url in ("/api/paper-rules", "/api/paper-rules/1", "/api/paper-rules/1/export.yaml"):
        assert client.get(url, headers=h(role)).status_code == 200
    assert client.post("/api/paper-rules/1/test", headers=h(role)).status_code == 403
    assert client.get("/api/papers/queue", headers=h(role)).status_code == 403
    assert (
        client.post("/api/paper-rules/drafts", json={"yaml": "x"}, headers=h(role)).status_code
        == 403
    )


@pytest.mark.parametrize("role", ["teacher", "mentor", "officer"])
def test_only_the_coach_opens_the_queue_and_changes_the_rules(
    client: TestClient, role: str
) -> None:
    assert client.get("/api/papers/queue", headers=h(role)).status_code == 403
    if role == "officer":
        assert client.get("/api/paper-rules", headers=h(role)).status_code == 403
    assert (
        client.post("/api/paper-rules/drafts", json={"yaml": "x"}, headers=h(role)).status_code
        == 403
    )
    assert client.get("/api/paper-rules", headers=h("coach")).status_code == 200
    assert client.get("/api/papers/queue", headers=h("coach")).status_code == 200


# 2026-11-01 (Papers page, DECISIONS): a mentor creates and assigns papers too, so only the officer
# is refused. The mentor's scope is enforced on assignment (tests/papers_hub).
@pytest.mark.parametrize("role", ["officer"])
def test_an_officer_cannot_generate_a_paper(client: TestClient, role: str) -> None:
    r = client.post("/api/papers/generate", json={"check": CHECK}, headers=h(role))
    assert r.status_code == 403


def test_a_teacher_generates_prints_and_gets_the_key_layout_map_and_twin(
    client: TestClient,
) -> None:
    out = gen(client)
    p, twin = out["paper"], out["twin"]
    assert p["status"] == "auto_approved" and p["printable"] and p["check_code"] == "PRE · 3A · T1"
    assert twin["form"] == "B" and twin["frozen"] and twin["twin_of"] == p["id"]
    pdf = client.get(f"/api/papers/{p['id']}/paper.pdf", headers=h("teacher"))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get(f"/api/papers/{p['id']}/key.pdf", headers=h("teacher")).status_code == 200
    other = client.get(f"/api/papers/{p['id']}/paper.pdf?layout=ta", headers=h("teacher"))
    assert other.status_code == 409  # Tamil wording is not approved with this English paper
    m = client.get(f"/api/papers/{p['id']}/layout.json?layout=hi", headers=h("teacher")).json()
    assert m["check_code"] == p["check_code"] and len(m["answer_boxes"]) == len(p["items"])
    key = client.get(f"/api/papers/{p['id']}/phone-key", headers=h("teacher")).json()
    assert key["paper_id"] == p["id"] and len(key["items"]) == len(p["items"])
    listed = client.get("/api/papers?class_id=c-0123456789", headers=h("teacher")).json()
    assert {x["id"] for x in listed} == {p["id"], twin["id"]}


def test_a_queued_paper_cannot_be_printed_until_the_coach_approves_it(client: TestClient) -> None:
    p = gen(client, language="ta")["paper"]
    assert p["status"] == "queued"
    assert client.get(f"/api/papers/{p['id']}/paper.pdf", headers=h("teacher")).status_code == 409
    assert client.get(f"/api/papers/{p['id']}/paper.pdf", headers=h("coach")).status_code == 200
    queue = client.get("/api/papers/queue", headers=h("coach")).json()
    assert any(q["paper"]["id"] == p["id"] and q["reason"] == "unreviewed_words" for q in queue)
    assert client.post(f"/api/papers/{p['id']}/approve", headers=h("teacher")).status_code == 403
    assert client.post(f"/api/papers/{p['id']}/approve", headers=h("coach")).status_code == 200
    assert client.get(f"/api/papers/{p['id']}/paper.pdf", headers=h("teacher")).status_code == 200


def test_a_rejection_keeps_the_reason(client: TestClient) -> None:
    p = gen(client, language="ta")["paper"]
    r = client.post(
        f"/api/papers/{p['id']}/reject", json={"reason": "Box 3 wording."}, headers=h("coach")
    )
    assert r.json()["status"] == "rejected" and r.json()["rejected_reason"] == "Box 3 wording."


def test_a_rule_change_goes_through_two_people(client: TestClient) -> None:
    rules = seed_rules()
    rules.template("sub-borrow").constraints["result_min"] = 11
    d = client.post(
        "/api/paper-rules/drafts", json={"yaml": to_yaml(rules)}, headers=h("coach", "a")
    )
    assert d.status_code == 200, d.text
    n = d.json()["number"]
    assert d.json()["status"] == "draft" and any("result_min" in x for x in d.json()["diff"])
    assert client.post(f"/api/paper-rules/{n}/submit", headers=h("coach", "a")).status_code == 200
    own = client.post(f"/api/paper-rules/{n}/publish", headers=h("coach", "a"))
    assert own.status_code == 403 and "second person" in own.text
    ok = client.post(f"/api/paper-rules/{n}/publish", headers=h("coach", "b"))
    assert ok.status_code == 200 and ok.json()["approver"] == "coach-b"
    listed = client.get("/api/paper-rules", headers=h("coach")).json()
    assert listed["published"] == n


def test_a_bad_rules_file_is_refused_with_its_reason(client: TestClient) -> None:
    r = client.post("/api/paper-rules/drafts", json={"yaml": "templates: 3"}, headers=h("coach"))
    assert r.status_code == 422


def test_test_this_rule_shows_sample_items_and_runs_the_checks(client: TestClient) -> None:
    r = client.post("/api/paper-rules/1/test", headers=h("coach")).json()
    assert len(r["samples"]["sub-borrow"]["items"]) == 5
    assert r["blueprints"]["standard_10_5"]["findings"] == []


def test_the_export_is_yaml_a_judge_can_read(client: TestClient) -> None:
    r = client.get("/api/paper-rules/1/export.yaml", headers=h("coach"))
    assert r.status_code == 200 and "sub-borrow" in r.text and "templates:" in r.text


def test_constraints_that_cannot_be_met_name_the_rule(client: TestClient) -> None:
    body = {
        "check": CHECK,
        "profile": {"source": "intake", "taught": [], "struggles": []},
        "blueprint": "standard_10_5",
    }
    r = client.post("/api/papers/generate", json=body, headers=h("teacher"))
    # nothing taught: no skill is assessed, so there is nothing to put on the paper
    assert r.status_code == 422 and r.json()["detail"]["rule"] == "coverage"


def test_a_request_with_a_childs_name_field_is_ignored_and_never_stored(client: TestClient) -> None:
    body = {
        "check": CHECK,
        "profile": {
            "source": "past",
            "counts": {"SUB-SFL": 9},
            "checked": 18,
            "children": [{"name": "Asha"}],
        },
    }
    p = client.post("/api/papers/generate", json=body, headers=h("teacher")).json()["paper"]
    assert "Asha" not in str(p)
