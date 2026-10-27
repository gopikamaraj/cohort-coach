"""P11 (reduced): the cohort API with real role checks. Who may do what, who sees what, and that no
handle, phone number or teacher id appears in any response."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

GOOD = "I used the bundles today and the children liked opening one."
DEVICES = [f"{i:016x}" for i in range(1, 7)]


def h(role: str, person: str | None = None, device: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    if person:
        out["X-Person"] = person
    if device:
        out["X-Device-Id"] = device
    return out


@pytest.fixture
def world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv(
        "JUDGE_MODE", "1"
    )  # roles other than teacher exist only in the judge deployment
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app(pilot=False)
    app.dependency_overrides[get_session] = session
    yield TestClient(app), factory


def open_cohort(
    c: TestClient, coach: str = "coach-1", mentors: tuple[str, ...] = ("mentor-1",)
) -> str:
    made = c.post(
        "/api/cohorts/officer/cohorts",
        json={
            "error": "SUB-SFL",
            "coach_id": coach,
            "mentor_ids": list(mentors),
            "school_count": 7,
        },
        headers=h("officer", "officer-1"),
    ).json()
    cid = made["id"]
    for to in ("active",):
        assert (
            c.post(
                f"/api/cohorts/officer/cohorts/{cid}/status", json={"to": to}, headers=h("officer")
            ).status_code
            == 200
        )
    for d in DEVICES:
        r = c.post(
            f"/api/cohorts/{cid}/join", json={"consent": True}, headers=h("teacher", device=d)
        )
        assert r.status_code == 200, r.text
    return cid


def test_joining_needs_the_teachers_own_tap_and_gives_a_system_label(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = c.post(
        "/api/cohorts/officer/cohorts",
        json={"error": "SUB-SFL", "coach_id": "coach-1"},
        headers=h("officer"),
    ).json()["id"]
    no = c.post(
        f"/api/cohorts/{cid}/join", json={"consent": False}, headers=h("teacher", device=DEVICES[0])
    )
    assert no.status_code == 403
    yes = c.post(
        f"/api/cohorts/{cid}/join", json={"consent": True}, headers=h("teacher", device=DEVICES[0])
    )
    assert yes.json()["display_name"] == "Teacher 1" and yes.json()["thread"] == "read_only"
    other = c.post(
        f"/api/cohorts/{cid}/join", json={"consent": True}, headers=h("teacher", device=DEVICES[1])
    )
    assert other.json()["display_name"] == "Teacher 2"


def test_a_post_reaches_the_other_members_and_a_made_up_child_name_is_blocked(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    ok = c.post(
        f"/api/cohorts/{cid}/posts",
        json={"body": GOOD, "language": "en"},
        headers=h("teacher", device=DEVICES[0]),
    )
    assert ok.status_code == 200 and ok.json()["author_name"] == "Teacher 1"
    bad = c.post(
        f"/api/cohorts/{cid}/posts",
        json={"body": "Meena failed again", "language": "en"},
        headers=h("teacher", device=DEVICES[0]),
    )
    assert bad.status_code == 422 and "child_name" in bad.json()["detail"]["codes"]
    seen = c.get(f"/api/cohorts/{cid}/thread", headers=h("teacher", device=DEVICES[3])).json()
    assert seen["state"] == "open" and [p["body"] for p in seen["posts"]] == [GOOD]


def test_a_report_holds_the_post_and_the_coach_hides_it(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    pid = c.post(
        f"/api/cohorts/{cid}/posts",
        json={"body": GOOD, "language": "en"},
        headers=h("teacher", device=DEVICES[0]),
    ).json()["id"]
    assert (
        c.post(
            f"/api/cohorts/posts/{pid}/report", headers=h("teacher", device=DEVICES[1])
        ).status_code
        == 200
    )
    assert (
        c.get(f"/api/cohorts/{cid}/thread", headers=h("teacher", device=DEVICES[2])).json()["posts"]
        == []
    )
    held = c.get(f"/api/cohorts/coach/cohorts/{cid}/thread", headers=h("coach", "coach-1")).json()
    assert [p["status"] for p in held] == ["reported"]
    done = c.post(
        f"/api/cohorts/coach/posts/{pid}/decide",
        json={"action": "hide"},
        headers=h("coach", "coach-1"),
    )
    assert done.json()["status"] == "hidden"


def test_a_mentor_sees_only_her_own_cohorts_and_never_a_member_list(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    mine = open_cohort(c, mentors=("mentor-1",))
    other = open_cohort(c, mentors=("mentor-2",))
    out = c.get("/api/cohorts/mentor/cohorts", headers=h("mentor", "mentor-1")).json()
    assert [x["id"] for x in out] == [mine]
    assert other not in json.dumps(out)
    assert not any(k in json.dumps(out) for k in ("teacher_id", "display_name", "members_list"))
    # and cannot read or post in another mentor's thread
    assert c.get(f"/api/cohorts/{other}/thread", headers=h("mentor", "mentor-1")).status_code == 403
    assert (
        c.post(
            f"/api/cohorts/{other}/posts", json={"body": GOOD}, headers=h("mentor", "mentor-1")
        ).status_code
        == 403
    )


def test_a_mentor_gets_cohort_level_figures_only(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    row = c.get("/api/cohorts/mentor/cohorts", headers=h("mentor", "mentor-1")).json()[0]
    assert set(row) == {
        "id",
        "error",
        "status",
        "track_version",
        "schools",
        "members",
        "thread",
        "simulated",
    }
    assert (
        row["members"] == 6 and row["schools"] == 7
    )  # six members: shown; under 5 it would be hidden
    small = c.post(
        "/api/cohorts/officer/cohorts",
        json={
            "error": "SUB-SFL",
            "coach_id": "coach-1",
            "mentor_ids": ["mentor-1"],
            "school_count": 2,
        },
        headers=h("officer"),
    ).json()
    assert small["members"] is None and small["schools"] is None  # fewer than 5: hidden
    assert cid


def test_a_coach_acts_only_on_her_assigned_cohorts(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c, coach="coach-1")
    pid = c.post(
        f"/api/cohorts/{cid}/posts",
        json={"body": GOOD, "language": "en"},
        headers=h("teacher", device=DEVICES[0]),
    ).json()["id"]
    stranger = h("coach", "coach-2")
    assert c.get("/api/cohorts/coach/cohorts", headers=stranger).json() == []
    assert c.get(f"/api/cohorts/coach/cohorts/{cid}/thread", headers=stranger).status_code == 403
    assert (
        c.post(
            f"/api/cohorts/coach/posts/{pid}/decide", json={"action": "hide"}, headers=stranger
        ).status_code
        == 403
    )
    assert (
        c.post(
            f"/api/cohorts/coach/cohorts/{cid}/prompt",
            json={"body": "Try bundles."},
            headers=stranger,
        ).status_code
        == 403
    )
    assert c.post(f"/api/cohorts/coach/cohorts/{cid}/closing", headers=stranger).status_code == 403
    assert c.get("/api/cohorts/coach/cohorts", headers=h("coach", "coach-1")).json()[0]["id"] == cid


def test_mentor_items_reach_the_coach_who_decides_and_a_mentor_cannot_approve(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    made = c.post(
        "/api/cohorts/mentor/items",
        json={"cohort_id": cid, "kind": "recording"},
        headers=h("mentor", "mentor-1"),
    ).json()
    assert made["status"] == "draft"
    sub = c.post(
        f"/api/cohorts/mentor/items/{made['id']}/submit", headers=h("mentor", "mentor-1")
    ).json()
    assert sub["status"] == "awaiting_coach"
    assert c.get("/api/cohorts/coach/items", headers=h("coach", "coach-2")).json() == []
    waiting = c.get("/api/cohorts/coach/items", headers=h("coach", "coach-1")).json()
    assert [i["id"] for i in waiting] == [made["id"]]
    deny = c.post(
        f"/api/cohorts/coach/items/{made['id']}/decide",
        json={"decision": "approve"},
        headers=h("mentor", "mentor-1"),
    )
    assert deny.status_code == 403
    bad = c.post(
        f"/api/cohorts/coach/items/{made['id']}/decide",
        json={"decision": "reject"},
        headers=h("coach", "coach-1"),
    )
    assert bad.status_code == 422
    ok = c.post(
        f"/api/cohorts/coach/items/{made['id']}/decide",
        json={"decision": "approve"},
        headers=h("coach", "coach-1"),
    )
    assert ok.json()["status"] == "approved"
    mine = c.get("/api/cohorts/mentor/items", headers=h("mentor", "mentor-1")).json()
    assert mine[0]["status"] == "approved"


def test_a_teacher_cannot_use_the_staff_routes_and_staff_cannot_use_officer_routes(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    routes = [
        ("get", "/api/cohorts/coach/cohorts"),
        ("get", "/api/cohorts/mentor/cohorts"),
        ("get", "/api/cohorts/officer/cohorts"),
        ("post", "/api/cohorts/officer/retention/run"),
        ("get", "/api/cohorts/coach/items"),
    ]
    for method, path in routes:
        assert (
            getattr(c, method)(path, headers=h("teacher", device=DEVICES[0])).status_code == 403
        ), path
    for role in ("coach", "mentor"):
        r = c.post(
            f"/api/cohorts/officer/cohorts/{cid}/status",
            json={"to": "cancelled"},
            headers=h(role, f"{role}-1"),
        )
        assert r.status_code == 403


def test_the_officer_closes_with_the_rule_and_the_thread_goes_read_only(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    cid = open_cohort(c)
    assert (
        c.post(f"/api/cohorts/coach/cohorts/{cid}/closing", headers=h("coach", "coach-1")).json()[
            "status"
        ]
        == "closing"
    )
    refuse = c.post(
        f"/api/cohorts/officer/cohorts/{cid}/status", json={"to": "closed"}, headers=h("officer")
    )
    assert refuse.status_code == 409
    done = c.post(
        f"/api/cohorts/officer/cohorts/{cid}/status",
        json={"to": "closed", "post_test_received": True},
        headers=h("officer"),
    )
    assert done.json()["status"] == "closed" and done.json()["thread"] == "read_only"
    r = c.post(
        f"/api/cohorts/{cid}/posts", json={"body": GOOD}, headers=h("teacher", device=DEVICES[0])
    )
    assert r.status_code == 409


def test_no_handle_phone_number_or_teacher_id_appears_in_any_response(world) -> None:  # type: ignore[no-untyped-def]
    c, factory = world
    cid = open_cohort(c)
    c.post(
        f"/api/cohorts/{cid}/posts",
        json={"body": GOOD, "language": "en"},
        headers=h("teacher", device=DEVICES[0]),
    )
    c.post(
        f"/api/cohorts/coach/cohorts/{cid}/prompt",
        json={"body": "This week try the bundles twice."},
        headers=h("coach", "coach-1"),
    )
    texts = [
        c.get(f"/api/cohorts/{cid}/thread", headers=h("teacher", device=DEVICES[1])).text,
        c.get(f"/api/cohorts/coach/cohorts/{cid}/thread", headers=h("coach", "coach-1")).text,
        c.get("/api/cohorts/coach/cohorts", headers=h("coach", "coach-1")).text,
        c.get("/api/cohorts/mentor/cohorts", headers=h("mentor", "mentor-1")).text,
    ]
    from services.api.db import Teacher

    with factory() as db:
        ids = [t.teacher_id for t in db.query(Teacher).all()]
    assert ids
    for text in texts:
        assert not any(i in text for i in ids) and "@" not in text
        assert not any(d in text for d in DEVICES)


def test_a_production_request_cannot_name_a_person_or_take_a_role(
    world, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert c.get("/api/cohorts/coach/cohorts", headers=h("coach", "coach-1")).status_code == 403


def test_retention_runs_through_the_officer_route(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    out = c.post("/api/cohorts/officer/retention/run", headers=h("officer")).json()
    assert out == {"held_bodies_erased": 0, "thread_text_erased": 0}
