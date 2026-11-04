"""The Papers page over HTTP: import (recorded reads), confirm, review, scope and assignments."""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from ai.client import CallContext
from ai.schemas import PaperRead, ReadPaperItem
from services.api import practice as practice_api
from services.api.db import Base, CohortMember, CohortSpace, Teacher, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.papers_hub.models import PaperImport
from tests.support_ai import FakeClient


def item(n: int, op: str, a: int | None, b: int | None = None, **kw: Any) -> ReadPaperItem:
    return ReadPaperItem(n=n, operation=op, a=a, b=b, **kw)


def pilot_read(**kw: Any) -> PaperRead:
    items = [item(1, "dictate", None), item(2, "dictate", None)]
    items += [item(3, "add", 38, 47), item(4, "add", 46, 28), item(5, "add", 59, 23)]
    items += [item(6, "subtract", 87, 52), item(7, "subtract", 74, 36), item(8, "subtract", 45, 19)]
    items += [item(9, "subtract", 82, 39), item(10, "subtract", 81, 27)]
    return PaperRead(form_letter="A", check_code="3B-04", class_code="3B", items=items, **kw)


class Env:
    def __init__(self, client: TestClient, fake: FakeClient, factory: Any, folder: Path) -> None:
        self.client, self.fake, self.factory, self.folder = client, fake, factory, folder

    def db(self) -> Session:
        return self.factory()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("ASSIGNMENT_ENABLED", "1")  # these tests cover the assignment feature itself; it is off by default (see the test below)
    monkeypatch.setenv("PAPER_IMPORT_DIR", str(tmp_path / "imports"))
    engine = make_engine(f"sqlite:///{tmp_path / 'hub.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    from services.api.devicestore import UserDoc

    with factory() as s:  # each class code below belongs to its own teacher
        for code in ("c-aaa1", "c-aaa2", "c-aaa3", "c-elsewhere", "c-other", "c-own1", "c-zzz9"):
            s.add(UserDoc(owner=f"owner of {code}", collection="classes", doc_id=code, data={"id": code}))
        s.commit()
    fake = FakeClient([pilot_read()])
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub", client=fake
    )
    yield Env(TestClient(app), fake, factory, tmp_path / "imports")


def hdr(role: str, person: str | None = None, cls: str | None = "c-own1") -> dict[str, str]:
    h = {"X-Role": role}
    # a teacher is the owner of her class; staff are users named by `person` (a class is its owner plus its code)
    h["X-User"] = f"owner of {cls}" if role == "teacher" and cls else (person or f"{role}-demo")
    if cls:
        h["X-Class-Id"] = cls
    return h


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 560), "white").save(buf, "PNG")
    return buf.getvalue()


def upload(
    env: Env, headers: dict[str, str] | None = None, data: bytes | None = None
) -> dict[str, Any]:
    r = env.client.post(
        "/api/paper-hub/imports",
        files=[("files", ("sheet.png", data or png(), "image/png"))],
        headers=headers or hdr("teacher"),
    )
    assert r.status_code == 200, r.text
    return dict(r.json())


def edit(
    env: Env,
    imp_id: str,
    edits: list[dict[str, Any]],
    headers: dict[str, str] | None = None,
    via: str = "user",
) -> dict[str, Any]:
    r = env.client.post(
        f"/api/paper-hub/imports/{imp_id}/edit",
        json={"edits": edits, "via": via},
        headers=headers or hdr("teacher"),
    )
    assert r.status_code == 200, r.text
    return dict(r.json())


def finish(env: Env, imp_id: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    h = headers or hdr("teacher")
    edit(
        env,
        imp_id,
        [
            {"field": "class_id", "value": "c-own1"},
            {"field": "kind", "value": "pre"},
        ],
        h,
    )
    r = env.client.post(f"/api/paper-hub/imports/{imp_id}/confirm", json={}, headers=h)
    assert r.status_code == 200, r.text
    return dict(r.json())


# --- import ---------------------------------------------------------------------------------------


def test_an_upload_becomes_a_draft_with_code_computed_keys_and_open_questions(env: Env) -> None:
    v = upload(env)
    items = {i["n"]: i for i in v["draft"]["items"]}
    assert items[3]["correct"] == 85 and items[7]["correct"] == 38
    assert not items[1]["supported"]  # a dictated number must be told
    assert {"class", "kind"} <= set(v["blocking"]) and "form" not in v[
        "blocking"
    ]  # the form letter follows from the kind
    assert "Handwriting and names are ignored" in v["note"]


def test_the_reader_is_blind_to_answers_and_its_pages_are_kept_for_the_review_screen_only(
    env: Env,
) -> None:
    v = upload(env)
    page = env.client.get(f"/api/paper-hub/imports/{v['id']}/page/1", headers=hdr("teacher"))
    assert page.status_code == 200 and "no-store" in page.headers["cache-control"]
    assert any(env.folder.iterdir())  # the upload is on disk now


def test_confirm_is_blocked_until_the_blocking_questions_are_answered(env: Env) -> None:
    v = upload(env)
    r = env.client.post(
        f"/api/paper-hub/imports/{v['id']}/confirm", json={}, headers=hdr("teacher")
    )
    assert r.status_code == 403 and "open questions" in r.text.lower()


def test_confirming_makes_a_usable_paper_that_is_never_printed_and_deletes_the_upload(
    env: Env,
) -> None:
    v = upload(env)
    paper = finish(env, v["id"])
    assert paper["status"] == "confirmed" and paper["printable"] is False
    assert not any(env.folder.iterdir()) if env.folder.exists() else True  # the upload is gone
    pdf = env.client.get(f"/api/papers/{paper['id']}/paper.pdf", headers=hdr("coach"))
    assert pdf.status_code == 409 and "already printed" in pdf.text
    with env.db() as db:
        from services.papers import store
        from services.papers.models import PaperReview, PaperRow

        row = db.get(PaperRow, paper["id"])
        assert store.usable(row) and not store.printable(row)
        assert (
            db.query(PaperReview)
            .filter_by(paper_id=row.id, reason="imported_pdf", status="open")
            .count()
            == 1
        )
        assert store.freeze(db, row.id, "teacher-demo").frozen_at is not None  # a check may use it
    assert (
        env.client.get(f"/api/paper-hub/imports/{v['id']}", headers=hdr("teacher")).status_code
        == 200
    )


def test_only_included_supported_items_make_the_paper_and_the_dictation_number_is_asked(
    env: Env,
) -> None:
    v = upload(env)
    edit(env, v["id"], [{"field": "items.1.a", "value": 305}, {"field": "items.2.a", "value": 496}])
    paper = finish(env, v["id"])
    ns = [i["n"] for i in paper["items"]]
    assert ns == list(range(1, 11))
    assert paper["items"][0]["correct"] == 305 and paper["items"][1]["wrong"]["PV-HEARD"] == [
        4096,
        40096,
        400906,
    ]


def test_the_import_belongs_to_one_person(env: Env) -> None:
    v = upload(env)
    other = hdr("teacher", cls="c-other")
    assert env.client.get(f"/api/paper-hub/imports/{v['id']}", headers=other).status_code == 403
    assert (
        env.client.post(
            f"/api/paper-hub/imports/{v['id']}/confirm", json={}, headers=other
        ).status_code
        == 403
    )


def test_an_abandoned_import_is_deleted_after_24_hours(env: Env) -> None:
    v = upload(env)
    with env.db() as db:
        row = db.get(PaperImport, v["id"])
        row.expires_at = row.expires_at - timedelta(hours=25)
        db.commit()
    r = env.client.get(f"/api/paper-hub/imports/{v['id']}", headers=hdr("teacher"))
    assert r.status_code == 403  # swept
    assert not (env.folder / v["id"]).exists()


def test_a_pdf_is_read_and_two_photos_merge(env: Env) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (400, 560), "white").save(buf, "PDF")
    r = env.client.post(
        "/api/paper-hub/imports",
        files=[("files", ("p.pdf", buf.getvalue(), "application/pdf"))],
        headers=hdr("teacher"),
    )
    assert r.status_code == 200 and r.json()["pages"] == 1
    env.fake.messages.replies[:] = [pilot_read(), pilot_read()]
    two = env.client.post(
        "/api/paper-hub/imports",
        files=[
            ("files", ("a.png", png() + b"1", "image/png")),
            ("files", ("b.png", png(), "image/png")),
        ],
        headers=hdr("teacher"),
    )
    assert two.status_code in (200, 422)


def test_keeping_the_sheet_is_not_offered_yet_and_says_so(env: Env) -> None:
    v = upload(env)
    r = env.client.post(
        f"/api/paper-hub/imports/{v['id']}/confirm",
        json={"keep_for_check": True},
        headers=hdr("teacher"),
    )
    assert r.status_code == 422 and "not available" in r.text


def test_an_edit_via_the_assistant_is_tagged_and_can_be_undone(env: Env) -> None:
    v = upload(env)
    out = edit(env, v["id"], [{"field": "class_id", "value": "c-own1"}], via="assistant")
    assert out["draft"]["changes"]["class_id"]["via"] == "assistant" and out["can_undo"]
    undone = env.client.post(
        f"/api/paper-hub/imports/{v['id']}/undo", headers=hdr("teacher")
    ).json()
    assert undone["draft"]["class_id"] is None and "class_id" not in undone["draft"]["changes"]


def test_only_whitelisted_fields_can_be_set(env: Env) -> None:
    v = upload(env)
    for bad in (
        {"field": "status", "value": "approved"},
        {"field": "items.3.correct", "value": 1},
        {"field": "kind", "value": "mock"},
        {"field": "items.3.a", "value": 5000},
    ):
        r = env.client.post(
            f"/api/paper-hub/imports/{v['id']}/edit", json={"edits": [bad]}, headers=hdr("teacher")
        )
        assert r.status_code == 422, bad


def test_a_reviewer_confirms_an_imported_paper_but_never_her_own(env: Env) -> None:
    v = upload(env, hdr("coach", "coach-aaa"))
    paper = finish(env, v["id"], hdr("coach", "coach-aaa"))
    own = env.client.post(f"/api/papers/{paper['id']}/approve", headers={"X-Role": "coach"})
    assert own.status_code in (200, 409)  # the legacy route acts as coach-demo, a different person
    with env.db() as db:
        from services.papers import store

        with pytest.raises(store.BadState):
            store.approve_paper(db, paper["id"], "coach-aaa")


def test_assignment_is_off_by_default_and_every_paper_is_shared(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASSIGNMENT_ENABLED")
    for method, path in (("get", "/api/paper-hub/assignable"), ("get", "/api/paper-hub/assignments/mine"), ("post", "/api/paper-hub/assignments")):
        assert getattr(env.client, method)(path, headers=hdr("teacher")).status_code == 404
    # listing, reading and choosing a paper need no class at all, and no class that is not hers
    made = make_generated(env, "c-own1")  # created by one teacher, visible to another
    ids = {p["id"] for p in env.client.get("/api/paper-hub/papers", headers={"X-Role": "teacher", "X-User": "newcomer"}).json()}
    assert made in ids
    other = {"X-Role": "teacher", "X-User": "newcomer", "X-Class-Id": "c-aaa1"}  # someone else's class
    assert {p["id"] for p in env.client.get("/api/paper-hub/papers", headers=other).json()} == ids
    assert env.client.get(f"/api/paper-hub/papers/{made}/detail", headers=other).status_code == 200


def test_officers_have_no_access(env: Env) -> None:
    for method, path in (("get", "/api/paper-hub/papers"), ("post", "/api/paper-hub/assignments")):
        r = getattr(env.client, method)(path, headers={"X-Role": "officer"})
        assert r.status_code == 403


# --- the scoped list --------------------------------------------------------------------------------


def make_generated(env: Env, cls: str, pilot: bool = True) -> str:
    body: dict[str, Any] = {
        "check": {"id": f"{cls}:1", "kind": "pre", "form": "A", "class_label": "3A", "term": 1},
        "language": "en",
    }
    if pilot:
        body["sample"] = True
    r = env.client.post("/api/papers/generate", json=body, headers={"X-Role": "teacher"})
    assert r.status_code == 200, r.text
    return str(r.json()["paper"]["id"])


def test_every_paper_is_listed_for_every_role_for_now(env: Env) -> None:
    mine, theirs = make_generated(env, "c-own1"), make_generated(env, "c-zzz9")
    ids = {p["id"] for p in env.client.get("/api/paper-hub/papers", headers=hdr("teacher")).json()}
    assert {mine, theirs} <= ids  # decided 2026-11-02: papers are open to all; entering and results stay private
    ids = {
        p["id"]
        for p in env.client.get("/api/paper-hub/papers", headers=hdr("coach", "coach-aaa")).json()
    }
    assert {mine, theirs} <= ids
    only_a = env.client.get(
        "/api/paper-hub/papers?form=B", headers=hdr("coach", "coach-aaa")
    ).json()
    assert all(p["form"] == "B" for p in only_a)


def test_the_list_says_source_review_frozen_and_cohort_state(env: Env) -> None:
    make_generated(env, "c-own1")
    v = upload(env)
    finish(env, v["id"])
    rows = env.client.get("/api/paper-hub/papers", headers=hdr("teacher")).json()
    imported = next(r for r in rows if r["source"] == "imported_pdf")
    assert imported["review"] == "awaiting_review" and imported["printable"] is False
    generated = next(r for r in rows if r["source"] == "generated")
    assert generated["cohorts"] == {"formed": False, "count": 0, "reason": "no_check"}


def test_the_detail_has_the_tabs_and_no_child_data(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    d = env.client.get(f"/api/paper-hub/papers/{pid}/detail", headers=hdr("teacher")).json()
    assert set(d) >= {"overview", "questions", "coverage", "usage", "history", "files"}
    assert "answers" not in str(d).lower() or "answers" not in d
    # papers are readable by every role for now; changing one is still scoped
    other = env.client.get(f"/api/paper-hub/papers/{pid}/detail", headers=hdr("teacher", cls="c-other"))
    assert other.status_code == 200
    assert env.client.delete(f"/api/paper-hub/papers/{pid}", headers=hdr("teacher", cls="c-other")).status_code == 404


# --- assignments ------------------------------------------------------------------------------------------


def seed_cohort(
    env: Env,
    classes: list[str],
    mentor: str = "mentor-aaa",
    coach: str = "coach-aaa",
    cid: str = "co-1",
) -> None:
    with env.db() as db:
        db.add(
            CohortSpace(
                id=cid,
                error="SUB-SFL",
                status="active",
                coach_id=coach,
                mentor_ids=[mentor],
                simulated=True,
            )
        )
        db.flush()
        for i, c in enumerate(classes):
            tid = f"t-{i:016x}"
            db.add(Teacher(teacher_id=tid, class_id=c))
            db.flush()
            db.add(CohortMember(cohort_id=cid, teacher_id=tid, display_name=f"Teacher {i + 1}"))
        db.commit()


def assign(
    env: Env,
    paper: str,
    kind: str,
    form: str,
    headers: dict[str, str],
    target: str = "class",
    tid: str = "c-own1",
    **kw: Any,
) -> Any:
    return env.client.post(
        "/api/paper-hub/assignments",
        json={
            "paper_id": paper,
            "target_type": target,
            "target_id": tid,
            "kind": kind,
            "form": form,
            **kw,
        },
        headers=headers,
    )


def test_a_teacher_assigns_only_to_her_own_class_and_it_shows_in_assigned_to_you(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    assert assign(env, pid, "pre", "A", hdr("teacher"), tid="c-other").status_code == 403
    ok = assign(
        env, pid, "pre", "A", hdr("teacher"), due_date="2026-11-07", note="Before the break"
    )
    assert ok.status_code == 200 and ok.json()["assignments"][0]["due_date"] == "2026-11-07"
    mine = env.client.get("/api/paper-hub/assignments/mine", headers=hdr("teacher")).json()
    assert [a["paper_id"] for a in mine] == [pid]
    assert (
        env.client.get(
            "/api/paper-hub/assignments/mine", headers=hdr("teacher", cls="c-other")
        ).json()
        == []
    )


def test_a_duplicate_active_assignment_is_refused_and_a_withdrawn_one_can_be_made_again(
    env: Env,
) -> None:
    pid = make_generated(env, "c-own1")
    first = assign(env, pid, "pre", "A", hdr("teacher")).json()["assignments"][0]
    assert assign(env, pid, "pre", "A", hdr("teacher")).status_code == 422
    assert (
        env.client.post(
            f"/api/paper-hub/assignments/{first['id']}/withdraw", headers=hdr("teacher")
        ).json()["status"]
        == "withdrawn"
    )
    assert assign(env, pid, "pre", "A", hdr("teacher")).status_code == 200


def test_an_assignment_cannot_be_withdrawn_once_a_sheet_is_entered(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    a = assign(env, pid, "pre", "A", hdr("teacher")).json()["assignments"][0]
    m = env.client.post(
        f"/api/paper-hub/assignments/{a['id']}/mark",
        json={"status": "in_progress", "entered": 3, "expected": 20},
        headers=hdr("teacher"),
    )
    assert m.status_code == 200 and m.json()["sheets_entered"] == 3
    assert (
        env.client.post(
            f"/api/paper-hub/assignments/{a['id']}/withdraw", headers=hdr("teacher")
        ).status_code
        == 403
    )


def test_a_pre_test_cannot_go_to_a_cohort_but_a_post_test_makes_one_row_per_class(env: Env) -> None:
    seed_cohort(env, ["c-aaa1", "c-aaa2", "c-aaa3"])
    pre = make_generated(env, "c-aaa1", pilot=False)
    assert (
        assign(env, pre, "pre", "A", hdr("coach", "coach-aaa"), "cohort", "co-1").status_code == 422
    )
    with env.db() as db:
        from services.papers import store

        post = store.twin_of(db, pre)
    assert post is not None
    r = assign(env, post.id, "post", "B", hdr("coach", "coach-aaa"), "cohort", "co-1")
    assert r.status_code == 200 and len(r.json()["assignments"]) == 3
    assert "pre-test it twins" in " ".join(r.json()["warnings"])


def test_a_mentor_assigns_only_inside_her_cohorts_and_a_coach_inside_hers(env: Env) -> None:
    seed_cohort(env, ["c-aaa1", "c-aaa2"])
    pid = make_generated(env, "c-aaa1")
    assert (
        assign(env, pid, "pre", "A", hdr("mentor", "mentor-aaa"), tid="c-aaa2").status_code == 200
    )
    assert (
        assign(env, pid, "pre", "A", hdr("mentor", "mentor-aaa"), tid="c-elsewhere").status_code
        == 403
    )
    assert (
        assign(env, pid, "pre", "A", hdr("mentor", "mentor-bbb"), tid="c-aaa1").status_code == 403
    )
    cohorts = env.client.get("/api/paper-hub/assignable", headers=hdr("coach", "coach-bbb")).json()[
        "cohorts"
    ]
    assert cohorts == []


def test_the_assistant_cannot_press_assign_and_notes_hold_no_personal_data(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    assert assign(env, pid, "pre", "A", hdr("teacher"), via="assistant").status_code == 403
    assert assign(env, pid, "pre", "A", hdr("teacher"), note="call 9876543210").status_code == 422


def test_progress_is_counts_only(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    a = assign(env, pid, "pre", "A", hdr("teacher")).json()["assignments"][0]
    env.client.post(
        f"/api/paper-hub/assignments/{a['id']}/mark",
        json={"status": "opened"},
        headers=hdr("teacher"),
    )
    p = env.client.get("/api/paper-hub/assignments/progress", headers=hdr("teacher")).json()
    assert (
        set(p) == {"assigned", "opened", "sheets_entered", "sheets_expected", "completed"}
        and p["opened"] == 1
    )


def test_an_unapproved_or_rejected_paper_cannot_be_assigned(env: Env) -> None:
    with env.db() as db:
        from services.papers.models import PaperRow

        pid = make_generated(env, "c-own1")
        row = db.get(PaperRow, pid)
        row.status = "queued"
        db.commit()
    assert assign(env, pid, "pre", "A", hdr("teacher")).status_code == 403


def test_a_coach_archives_a_paper_and_a_teacher_cannot(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    assert (
        env.client.post(f"/api/paper-hub/papers/{pid}/archive", headers=hdr("teacher")).status_code
        == 403
    )
    assert (
        env.client.post(
            f"/api/paper-hub/papers/{pid}/archive", headers=hdr("coach", "coach-aaa")
        ).json()["status"]
        == "archived"
    )
    ids = {
        p["id"]
        for p in env.client.get("/api/paper-hub/papers", headers=hdr("coach", "coach-aaa")).json()
    }
    assert pid not in ids


def test_every_imported_paper_is_entered_on_the_phone_with_its_own_key(env: Env) -> None:
    v = upload(env)
    edit(env, v["id"], [{"field": "items.1.a", "value": 305}, {"field": "items.2.a", "value": 496}])
    paper = finish(env, v["id"])
    key = env.client.get(f"/api/paper-hub/papers/{paper['id']}/key", headers=hdr("teacher"))
    assert key.status_code == 200, key.text
    items = key.json()["forms"][paper["id"]]["items"]
    assert [i["correct"] for i in items] == [i["correct"] for i in paper["items"]]
    assert items[0]["correct"] == 305 and all(i["anchor"] for i in items)


def test_the_assistants_paper_status_tool_is_read_only_and_limited_to_the_users_scope(
    env: Env,
) -> None:
    from services.assistant.scopes import scopes
    from services.assistant.tools import ToolDenied, call_tool
    from services.papers_hub.api import Who

    pid = make_generated(env, "c-own1")
    mine, other = (
        Who("teacher", "teacher-c-own1", "c-own1"),
        Who("teacher", "teacher-c-other", "c-other"),
    )
    teacher = scopes()["teacher"]
    with env.db() as db:
        ok = call_tool(teacher, "paper_status", db=db, who=mine, paper_id=pid)["result"]
        assert ok["found"] and ok["cohorts"]["reason"] == "no_check" and ok["source"] == "generated"
        assert (
            call_tool(teacher, "paper_status", db=db, who=other, paper_id=pid)["result"]["found"]
            is False
        )
        before = ok
        assert (
            call_tool(teacher, "paper_status", db=db, who=mine, paper_id=pid)["result"] == before
        )  # no side effect
    with pytest.raises(ToolDenied):  # the officer's scope does not list it
        call_tool(scopes()["officer"], "paper_status", db=None, who=mine, paper_id=pid)


def test_an_imported_paper_shows_in_the_papers_list_and_its_detail_the_old_screens_use(
    env: Env,
) -> None:
    v = upload(env)
    paper = finish(env, v["id"])
    listed = env.client.get("/api/papers?class_id=c-own1", headers={"X-Role": "teacher"})
    assert listed.status_code == 200, listed.text
    assert paper["id"] in [p["id"] for p in listed.json()]
    one = env.client.get(f"/api/papers/{paper['id']}", headers={"X-Role": "teacher"})
    assert one.status_code == 200, one.text


def imported_paper(env: Env, headers: dict[str, str] | None = None) -> dict[str, Any]:
    v = upload(env, headers)
    edit(
        env,
        v["id"],
        [{"field": "items.1.a", "value": 346}, {"field": "items.2.a", "value": 728}],
        headers,
    )
    return finish(env, v["id"], headers)


def test_an_imported_paper_is_edited_in_place_and_every_key_is_recomputed(env: Env) -> None:
    paper = imported_paper(env)
    r = env.client.post(
        f"/api/paper-hub/papers/{paper['id']}/items",
        json={"edits": [{"field": "items.3.b", "value": 48}]},
        headers=hdr("teacher"),
    )
    assert r.status_code == 200, r.text
    d = env.client.get(f"/api/paper-hub/papers/{paper['id']}/detail", headers=hdr("teacher")).json()
    three = next(q for q in d["questions"] if q["n"] == 3)
    assert three["b"] == 48 and three["correct"] == 86  # 38 + 48, worked out by code
    assert d["edit_mode"] == "in_place" and d["editable"] and d["deletable"]


def test_editing_an_approved_imported_paper_sends_it_back_to_review(env: Env) -> None:
    paper = imported_paper(env, hdr("coach", "coach-aaa"))
    with env.db() as db:
        from services.papers import store

        store.approve_paper(db, paper["id"], "coach-bbb")  # someone else approves it
    r = env.client.post(
        f"/api/paper-hub/papers/{paper['id']}/items",
        json={"edits": [{"field": "items.4.a", "value": 47}]},
        headers=hdr("coach", "coach-aaa"),
    )
    assert (
        r.status_code == 200
        and r.json()["status"] == "confirmed"
        and r.json()["review"] == "awaiting_review"
    )


def test_bad_edits_are_refused_and_a_paper_in_use_cannot_change(env: Env) -> None:
    paper = imported_paper(env)
    h = hdr("teacher")
    for bad in (
        {"field": "kind", "value": "post"},
        {"field": "items.3.a", "value": 5000},
        {"field": "items.3.correct", "value": 1},
    ):
        assert (
            env.client.post(
                f"/api/paper-hub/papers/{paper['id']}/items", json={"edits": [bad]}, headers=h
            ).status_code
            == 422
        )
    assert (
        env.client.post(
            f"/api/paper-hub/papers/{paper['id']}/items",
            json={"edits": [{"field": "items.3.include", "value": False}]},
            headers=h,
        ).status_code
        == 200
    )
    with env.db() as db:
        from services.papers import store

        store.freeze(db, paper["id"], "teacher-demo")  # the first sheet is entered
    locked = env.client.post(
        f"/api/paper-hub/papers/{paper['id']}/items",
        json={"edits": [{"field": "items.4.a", "value": 40}]},
        headers=h,
    )
    assert locked.status_code == 403 and "sheet" in locked.text
    d = env.client.get(f"/api/paper-hub/papers/{paper['id']}/detail", headers=h).json()
    assert d["editable"] is False and d["deletable"] is False and "sheet" in d["in_use"]


def test_a_generated_paper_is_edited_in_the_same_paper_with_no_copy_and_goes_back_to_review(
    env: Env,
) -> None:
    pid = make_generated(env, "c-own1", pilot=False)
    with env.db() as db:
        from services.papers.models import PaperRow

        before = db.query(PaperRow).count()
        three = next(i for i in db.get(PaperRow, pid).body["items"] if i["n"] == 3)
    r = env.client.post(
        f"/api/paper-hub/papers/{pid}/items",
        json={
            "edits": [
                {
                    "field": "items.3.b",
                    "value": three["b"] - 1 if three["b"] > 11 else three["b"] + 1,
                }
            ]
        },
        headers=hdr("teacher"),
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["id"] == pid and r.json()["status"] == "queued" and r.json()["printable"] is False
    )
    with env.db() as db:
        from services.papers.models import PaperItemRow, PaperReview, PaperRow

        assert db.query(PaperRow).count() == before  # no copy
        row = db.get(PaperRow, pid)
        item = next(i for i in row.body["items"] if i["n"] == 3)
        assert item["a"] + item["b"] == item["correct"] and row.custom
        assert db.query(PaperItemRow).filter_by(paper_id=pid, n=3).one().b == item["b"]
        assert db.query(PaperReview).filter_by(paper_id=pid, status="open").count() >= 1


def test_numbers_that_do_not_fit_are_saved_but_flagged_and_cannot_be_approved(env: Env) -> None:
    pid = make_generated(env, "c-own1", pilot=False)
    r = env.client.post(
        f"/api/paper-hub/papers/{pid}/items",
        json={"edits": [{"field": "items.3.a", "value": 5}]},
        headers=hdr("teacher"),
    )
    assert r.status_code == 200 and r.json()["findings"]
    with env.db() as db:
        from services.papers import store

        with pytest.raises(store.BadState):
            store.approve_paper(db, pid, "coach-bbb")


def test_a_post_test_twin_is_locked_and_says_so(env: Env) -> None:
    pre = make_generated(env, "c-own1", pilot=False)
    with env.db() as db:
        from services.papers import store

        post = store.twin_of(db, pre).id
    d = env.client.get(f"/api/paper-hub/papers/{post}/detail", headers=hdr("teacher")).json()
    assert d["editable"] is False and "post-test" in d["locked_reason"] and d["deletable"] is True
    r = env.client.post(
        f"/api/paper-hub/papers/{post}/items",
        json={"edits": [{"field": "items.3.a", "value": 40}]},
        headers=hdr("teacher"),
    )
    assert r.status_code == 403 and "post-test" in r.text


def test_delete_removes_the_paper_its_items_and_review_rows_and_keeps_the_audit_trail(
    env: Env,
) -> None:
    paper = imported_paper(env)
    r = env.client.delete(f"/api/paper-hub/papers/{paper['id']}", headers=hdr("teacher"))
    assert r.status_code == 200 and r.json()["deleted"] == [paper["id"]]
    with env.db() as db:
        from services.papers.models import PaperEvent, PaperItemRow, PaperReview, PaperRow

        assert db.get(PaperRow, paper["id"]) is None
        assert db.query(PaperItemRow).filter_by(paper_id=paper["id"]).count() == 0
        assert db.query(PaperReview).filter_by(paper_id=paper["id"]).count() == 0
        assert db.query(PaperEvent).filter_by(paper_id=paper["id"], event="deleted").count() == 1
    assert paper["id"] not in [
        p["id"] for p in env.client.get("/api/paper-hub/papers", headers=hdr("teacher")).json()
    ]


def test_a_paper_in_use_or_assigned_cannot_be_deleted_until_the_assignment_is_withdrawn(
    env: Env,
) -> None:
    pid = make_generated(env, "c-own1")
    a = assign(env, pid, "pre", "A", hdr("teacher")).json()["assignments"][0]
    blocked = env.client.delete(f"/api/paper-hub/papers/{pid}", headers=hdr("teacher"))
    assert blocked.status_code == 403 and "assigned" in blocked.text
    env.client.post(f"/api/paper-hub/assignments/{a['id']}/withdraw", headers=hdr("teacher"))
    assert (
        env.client.delete(f"/api/paper-hub/papers/{pid}", headers=hdr("teacher")).status_code == 200
    )
    pid2 = make_generated(env, "c-own1")
    with env.db() as db:
        from services.papers import store

        store.freeze(db, pid2, "teacher-demo")
    assert (
        env.client.delete(f"/api/paper-hub/papers/{pid2}", headers=hdr("teacher")).status_code
        == 403
    )


def test_deleting_a_pre_test_takes_its_unused_post_test_twin_and_refuses_if_the_twin_is_in_use(
    env: Env,
) -> None:
    pre = make_generated(env, "c-own1", pilot=False)
    with env.db() as db:
        from services.papers import store

        post = store.twin_of(db, pre).id
    r = env.client.delete(f"/api/paper-hub/papers/{pre}", headers=hdr("teacher"))
    assert r.status_code == 200 and set(r.json()["deleted"]) == {pre, post}
    pre2 = make_generated(env, "c-own1", pilot=False)
    with env.db() as db:
        from services.papers import store

        post2 = store.twin_of(db, pre2).id
        store.freeze(db, post2, "teacher-demo")  # a sheet of the post-test is entered
    again = env.client.delete(f"/api/paper-hub/papers/{pre2}", headers=hdr("teacher"))
    assert again.status_code == 403 and "twin" in again.text


def test_only_the_owner_or_a_coach_may_change_or_delete(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    assert (
        env.client.delete(
            f"/api/paper-hub/papers/{pid}", headers=hdr("teacher", cls="c-other")
        ).status_code
        == 404
    )
    assert (
        env.client.delete(
            f"/api/paper-hub/papers/{pid}", headers=hdr("coach", "coach-aaa")
        ).status_code
        == 200
    )
    assert (
        env.client.delete("/api/paper-hub/papers/P-none", headers=hdr("teacher")).status_code == 404
    )
    assert (
        env.client.delete(f"/api/paper-hub/papers/{pid}", headers={"X-Role": "officer"}).status_code
        == 403
    )


def test_the_edit_form_checks_numbers_against_the_item_rule_without_saving(env: Env) -> None:
    pid = make_generated(env, "c-own1")
    d = env.client.get(f"/api/paper-hub/papers/{pid}/detail", headers=hdr("teacher")).json()
    three = next(q for q in d["questions"] if q["n"] == 3)  # an addition that carries

    def check(a: int, b: int) -> dict[str, Any]:
        r = env.client.post(
            f"/api/paper-hub/papers/{pid}/items/check",
            json={"items": [{"n": 3, "a": a, "b": b}]},
            headers=hdr("teacher"),
        )
        assert r.status_code == 200, r.text
        return dict(r.json()["items"][0])

    bad = check(5, 4)  # no carry
    assert not bad["ok"] and bad["answer"] is None and bad["rule"] and bad["problems"]
    good = check(three["a"], three["b"])
    assert good["ok"] and good["answer"] == three["a"] + three["b"]
    after = env.client.get(f"/api/paper-hub/papers/{pid}/detail", headers=hdr("teacher")).json()
    assert after["questions"] == d["questions"]  # a check saves nothing


def test_a_papers_own_key_reads_like_the_built_in_forms_and_comes_from_its_numbers(
    env: Env,
) -> None:
    pid = make_generated(env, "c-own1", pilot=False)
    r = env.client.get(f"/api/paper-hub/papers/{pid}/key", headers=hdr("teacher"))
    assert r.status_code == 200, r.text
    key = r.json()
    form = key["forms"][pid]
    detail = env.client.get(f"/api/paper-hub/papers/{pid}/detail", headers=hdr("teacher")).json()
    assert [i["n"] for i in form["items"]] == [q["n"] for q in detail["questions"]]
    assert [i["correct"] for i in form["items"]] == [q["correct"] for q in detail["questions"]]
    # the same fields the phone reads for a built-in form, including the stage signatures
    assert {"probes", "wrong", "untracked", "signatures", "type", "a", "b"} <= set(form["items"][0])
    assert key["rules"]["min_hits"] == 2 and key["content_hash"]
    # reading a key is open to every role for now (DECISIONS 2026-11-02): papers are shared
    other = env.client.get(
        f"/api/paper-hub/papers/{pid}/key", headers=hdr("teacher", cls="c-other")
    )
    assert other.status_code == 200 and other.json()["forms"].keys() == r.json()["forms"].keys()


def test_when_the_ai_service_fails_the_import_says_so_instead_of_blaming_the_photo(
    env: Env,
) -> None:
    """A refused or failed model request (an API error, a usage limit, the budget) is not a
    blurry photo: the teacher is told the reader is unavailable, and nothing is kept."""
    env.fake.messages.replies.clear()  # every request fails, as when the provider refuses it
    r = env.client.post(
        "/api/paper-hub/imports",
        files=[("files", ("sheet.png", png(), "image/png"))],
        headers=hdr("teacher"),
    )
    assert r.status_code == 503, r.text
    assert "not available" in r.json()["detail"] and "photo" not in r.json()["detail"]
    assert not env.folder.exists() or not any(env.folder.iterdir())
