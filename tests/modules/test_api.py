# ruff: noqa: E501
"""The module endpoints: a teacher sees her own track, a coach sees counts, the job endpoint is guarded."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.modules import api as modules_api
from services.modules.service import IST

DEV1, DEV2 = f"{1:016x}", f"{2:016x}"
BODY = {
    "check_id": "c-abc:1",
    "name": "My class: carrying",
    "errors": ["ADD-NOCARRY"],
    "counts": {"ADD-NOCARRY": 6},
    "children_checked": 20,
}
NOW = {"t": datetime(2026, 11, 2, 10, 0, tzinfo=IST)}


def h(role: str, device: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    if device:
        out["X-Device-Id"] = device
    return out


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    NOW["t"] = datetime(2026, 11, 2, 10, 0, tzinfo=IST)
    monkeypatch.setattr(modules_api, "clock", lambda: NOW["t"])
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def make_cohort(client: TestClient, device: str = DEV1) -> str:
    r = client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", device))
    assert r.status_code == 200, r.text
    return str(r.json()["id"])


def start(client: TestClient, cid: str, device: str = DEV1, language: str = "en") -> dict:
    r = client.post(
        "/api/modules/tracks",
        json={"cohort_id": cid, "error": "ADD-NOCARRY", "language": language},
        headers=h("teacher", device),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_a_teacher_starts_a_track_and_gets_module_one_only(client: TestClient) -> None:
    view = start(client, make_cohort(client))
    assert [m["status"] for m in view["modules"]] == ["ready", "planned", "planned"]
    assert view["current"] == 1 and view["total"] == 3
    assert view["modules"][0]["reason_text"] and view["modules"][0]["spoken"].startswith(
        "Module 1 of 3"
    )
    assert "text" not in view["modules"][1]


def test_get_next_is_blocked_with_a_reason_and_works_after_feedback(client: TestClient) -> None:
    cid = make_cohort(client)
    view = start(client, cid)
    tid = view["id"]
    assert view["can_next"]["code"] == "needs_feedback"
    r = client.post(f"/api/modules/tracks/{tid}/next", headers=h("teacher", DEV1))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "needs_feedback"
    r = client.post(
        f"/api/modules/tracks/{tid}/modules/1/feedback",
        json={"answer": "partly", "note": ""},
        headers=h("teacher", DEV1),
    )
    assert r.status_code == 200 and r.json()["can_next"]["enabled"] is True
    NOW["t"] += timedelta(days=1)
    r = client.post(f"/api/modules/tracks/{tid}/next", headers=h("teacher", DEV1))
    assert r.status_code == 200
    second = r.json()["modules"][1]
    assert second["status"] == "ready" and second["branch"] == "partly"
    assert (
        second["title"] == view["modules"][0]["title"]
    )  # the same approach again, as a smaller step


def test_a_double_press_gives_one_module(client: TestClient) -> None:
    tid = start(client, make_cohort(client))["id"]
    client.post(
        f"/api/modules/tracks/{tid}/modules/1/feedback",
        json={"answer": "worked"},
        headers=h("teacher", DEV1),
    )
    a = client.post(f"/api/modules/tracks/{tid}/next", headers=h("teacher", DEV1))
    b = client.post(f"/api/modules/tracks/{tid}/next", headers=h("teacher", DEV1))
    assert a.status_code == 200
    assert b.status_code == 409  # now she has not answered Module 2, so the button is closed again
    assert [m["number"] for m in a.json()["modules"]] == [1, 2, 3]


def test_another_teacher_cannot_see_or_change_the_track(client: TestClient) -> None:
    tid = start(client, make_cohort(client))["id"]
    assert client.get(f"/api/modules/tracks/{tid}", headers=h("teacher", DEV2)).status_code == 403
    r = client.post(
        f"/api/modules/tracks/{tid}/modules/1/feedback",
        json={"answer": "worked"},
        headers=h("teacher", DEV2),
    )
    assert r.status_code == 403
    assert client.get("/api/modules/tracks", headers=h("teacher", DEV2)).json() == []


def test_a_teacher_cannot_start_a_track_on_someone_elses_cohort(client: TestClient) -> None:
    cid = make_cohort(client)
    r = client.post(
        "/api/modules/tracks",
        json={"cohort_id": cid, "error": "ADD-NOCARRY"},
        headers=h("teacher", DEV2),
    )
    assert r.status_code == 404


def test_the_downloaded_call_marks_the_module(client: TestClient) -> None:
    tid = start(client, make_cohort(client))["id"]
    r = client.post(
        f"/api/modules/tracks/{tid}/modules/1/downloaded",
        json={"audio_ref": "pack-audio/x.mp3"},
        headers=h("teacher", DEV1),
    )
    assert r.status_code == 200 and r.json()["modules"][0]["status"] == "downloaded"


def test_the_coach_sees_counts_and_no_teacher(client: TestClient) -> None:
    cid = make_cohort(client)
    tid = start(client, cid)["id"]
    client.post(
        f"/api/modules/tracks/{tid}/modules/1/feedback",
        json={"answer": "worked"},
        headers=h("teacher", DEV1),
    )
    r = client.get(f"/api/modules/coach/cohorts/{cid}", headers=h("coach"))
    assert r.status_code == 200
    body = r.json()
    assert body["modules"][0]["feedback"]["worked"] == 1 and body["tracks"] == 1
    assert DEV1 not in r.text and "teacher_id" not in r.text


def test_roles_are_enforced(client: TestClient) -> None:
    cid = make_cohort(client)
    start(client, cid)
    assert (
        client.get(f"/api/modules/coach/cohorts/{cid}", headers=h("teacher", DEV1)).status_code
        == 403
    )
    assert client.get("/api/modules/tracks", headers=h("coach")).status_code in (403, 422)
    shift = client.post(
        f"/api/modules/coach/cohorts/{cid}/shift",
        json={"days": 3, "reason": "holiday"},
        headers=h("teacher", DEV1),
    )
    assert shift.status_code == 403


def test_a_coach_shifts_dates_and_the_teacher_sees_the_new_ones(client: TestClient) -> None:
    cid = make_cohort(client)
    view = start(client, cid)
    r = client.post(
        f"/api/modules/coach/cohorts/{cid}/shift",
        json={"days": 3, "reason": "holiday"},
        headers=h("coach"),
    )
    assert r.status_code == 200 and r.json()["moved"] == 2
    after = client.get(f"/api/modules/tracks/{view['id']}", headers=h("teacher", DEV1)).json()
    assert [m["due_date"] for m in after["modules"]][0] == view["modules"][0]["due_date"]
    assert after["modules"][1]["due_date"] != view["modules"][1]["due_date"]
    bad = client.post(
        f"/api/modules/coach/cohorts/{cid}/shift",
        json={"days": 3, "reason": "x"},
        headers=h("coach"),
    )
    assert bad.status_code == 200
    one = client.post(
        f"/api/modules/coach/cohorts/{cid}/modules/1/due",
        json={"due_date": "2026-12-01", "reason": "x"},
        headers=h("coach"),
    )
    assert one.status_code == 409 and one.json()["detail"]["code"] == "fixed_date"


def test_the_job_endpoint_is_off_without_its_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MODULES_JOB_TOKEN", raising=False)
    assert client.post("/api/modules/jobs/due").status_code == 403
    monkeypatch.setenv("MODULES_JOB_TOKEN", "s3cret")
    assert client.post("/api/modules/jobs/due", headers={"X-Job-Token": "wrong"}).status_code == 403


def test_the_job_endpoint_runs_the_job_with_the_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = make_cohort(client)
    tid = start(client, cid)["id"]
    monkeypatch.setenv("MODULES_JOB_TOKEN", "s3cret")
    NOW["t"] += timedelta(days=7, hours=-4)  # 06:00 on day 7
    r = client.post("/api/modules/jobs/due", headers={"X-Job-Token": "s3cret"})
    assert r.status_code == 200 and r.json()["generated"] == 1
    again = client.post("/api/modules/jobs/due", headers={"X-Job-Token": "s3cret"})
    assert again.json()["generated"] == 0
    got = client.get(f"/api/modules/tracks/{tid}", headers=h("teacher", DEV1)).json()
    assert got["modules"][1]["branch"] == "no_feedback"


def test_refreshing_the_tts_text_is_testing_only_and_keeps_the_code_script_when_ai_is_off(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    view = start(client, make_cohort(client))
    url = f"/api/modules/tracks/{view['id']}/modules/1/narration/refresh"
    monkeypatch.setenv("DEV_TESTING", "0")
    assert client.post(url, headers=h("teacher", DEV1)).status_code == 404
    monkeypatch.setenv("DEV_TESTING", "1")
    monkeypatch.setenv("AI_MODE", "off")
    r = client.post(url, headers=h("teacher", DEV1))
    assert r.status_code == 200, r.text
    assert r.json()["reworded"] is False
    spoken = r.json()["track"]["modules"][0]["spoken"]
    assert "What this does. [pause] " in spoken
    assert client.post(url.replace("modules/1", "modules/3"), headers=h("teacher", DEV1)).status_code == 409
