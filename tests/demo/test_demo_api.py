"""Demo Studio over HTTP: judge only, one session per device, Reset clears only its own data, the
AI read is cached by image hash and capped per session, and every answer is labelled simulated."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from ai.client import CallContext
from ai.schemas import SheetRead
from services.api import practice as practice_api
from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.demo import scenario, sheets
from tests.support_ai import FakeClient

S1, S2 = "demo-aaaaaaaa1111", "demo-bbbbbbbb2222"


class Env:
    def __init__(self, client: TestClient, fake: FakeClient) -> None:
        self.client, self.fake = client, fake


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    monkeypatch.setenv("DEMO_CACHE_DIR", str(tmp_path / "cache"))
    from services.demo import api as demo_api

    monkeypatch.setattr(demo_api, "CACHE", tmp_path / "cache")
    # a quick stand-in for the photo step: the drawn sheet, smaller, no camera effects
    monkeypatch.setattr(sheets, "photograph", lambda img, child, seed: img.resize((620, 877)))
    engine = make_engine(f"sqlite:///{tmp_path / 'demo.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    fake = FakeClient([])
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub", client=fake
    )
    yield Env(TestClient(app), fake)


def start(c: TestClient, sid: str = S1) -> dict[str, Any]:
    r = c.post("/api/demo/session", json={"session": sid})
    assert r.status_code == 200, r.text
    return dict(r.json())


def make_paper(c: TestClient, sid: str = S1) -> str:
    body = {
        "check": {
            "id": f"c-{sid[5:]}:1",
            "kind": "pre",
            "form": "A",
            "class_label": "3A",
            "term": 1,
        },
        "sample": True,
        "language": "en",
    }
    r = c.post("/api/papers/generate", json=body, headers={"X-Role": "teacher"})
    assert r.status_code == 200, r.text
    return str(r.json()["paper"]["id"])


def sheets_for(c: TestClient, sid: str = S1) -> dict[str, Any]:
    r = c.post(f"/api/demo/{sid}/sheets", json={"paper_id": make_paper(c, sid)})
    assert r.status_code == 200, r.text
    return dict(r.json())


def truth_read(roll: int = 1) -> SheetRead:
    demo = scenario.build_class(scenario.load_scenario())
    answers = list(demo.children[roll - 1].answers)
    return SheetRead(reads=[a or "" for a in answers], confidences=[0.97] * len(answers))


def test_the_demo_is_refused_outside_the_judge_deployment(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert env.client.post("/api/demo/session", json={"session": S1}).status_code == 404


def test_a_session_is_labelled_simulated_and_sessions_never_see_each_other(env: Env) -> None:
    a = start(env.client, S1)
    start(env.client, S2)
    assert a["simulated"] and "simulated" in a["label"].lower() and a["class_code"] == "3A"
    sheets_for(env.client, S1)
    assert env.client.get(f"/api/demo/{S1}/reads.json").status_code == 200
    assert env.client.get(f"/api/demo/{S2}/reads.json").status_code == 409  # S2 has no paper
    assert env.client.get("/api/demo/demo-cccccccc3333/reads.json").status_code == 404
    assert env.client.get("/api/demo/../etc/reads.json").status_code in (404, 422)


def test_reset_clears_only_this_sessions_data(env: Env) -> None:
    start(env.client, S1)
    start(env.client, S2)
    assert env.client.delete(f"/api/demo/session/{S1}").json() == {"reset": True}
    assert env.client.get(f"/api/demo/session/{S1}").status_code == 404
    assert env.client.get(f"/api/demo/session/{S2}").status_code == 200


def test_sheets_are_named_by_class_and_roll_and_the_zip_has_the_answer_file(env: Env) -> None:
    start(env.client)
    out = sheets_for(env.client)
    names = [s["name"] for s in out["sheets"]]
    assert names[0] == "3A-roll01.png" and len(names) == 20
    assert "synthetic" in out["label"]
    png = env.client.get(f"/api/demo/{S1}/sheets/3A-roll07.png")
    assert png.status_code == 200 and sheets.demo_flag(png.content)["demo-roll"] == "7"  # type: ignore[index]
    z = env.client.get(f"/api/demo/{S1}/sheets.zip")
    import zipfile

    zipped = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "reads.json" in zipped and "3A-roll20.png" in zipped and "3A-blank-paper.pdf" in zipped
    assert "truth.json" not in zipped


def test_sheet_1_is_read_by_the_ai_once_then_from_the_cache(env: Env) -> None:
    start(env.client)
    sheets_for(env.client)
    png = env.client.get(f"/api/demo/{S1}/sheets/3A-roll01.png").content
    env.fake.messages.replies.extend([truth_read(1)])  # one model reply only
    first = env.client.post(
        f"/api/demo/{S1}/read",
        files={"image": ("3A-roll01.png", png)},
        data={"name": "3A-roll01.png"},
    ).json()
    assert first["source"] == "ai" and first["label"] == "Read by AI" and not first["cached"]
    assert first["roll"] == 1 and first["demo_sheet"] and first["ai_reads"] == 1
    again = env.client.post(f"/api/demo/{S1}/read", files={"image": ("x.png", png)}).json()
    assert again["cached"] and again["ai_reads"] == 1  # no second model call
    other = start(env.client, S2)
    third = env.client.post(f"/api/demo/{S2}/read", files={"image": ("x.png", png)}).json()
    assert third["cached"] and other["ai_reads"] == 0
    summary = env.client.get(f"/api/demo/{S1}/reading-summary").json()
    assert summary["label"] == "Synthetic sheets" and "Not evidence" in summary["note"]
    assert summary["sheets_read_by_ai"] == 2 and summary["boxes"] == 20


def test_an_image_that_is_not_a_demo_sheet_is_read_by_the_ai(env: Env) -> None:
    start(env.client)
    buf = io.BytesIO()
    Image.new("RGB", (300, 400), "white").save(buf, "PNG")
    env.fake.messages.replies.extend([truth_read(1)])
    r = env.client.post(f"/api/demo/{S1}/read", files={"image": ("photo.png", buf.getvalue())})
    assert r.status_code == 200 and r.json()["demo_sheet"] is False and r.json()["roll"] is None


@pytest.mark.parametrize(
    "mode,words",
    [("recorded", "no recorded AI read"), ("off", "AI reader is off")],
)
def test_without_a_live_model_the_read_says_why_and_counts_nothing(
    env: Env, mode: str, words: str
) -> None:
    # Recorded mode cannot replay a read of a new sheet; off mode reads nothing. Each says so,
    # offers Auto-fill and typing, and adds nothing to the reading summary or the read count.
    from fastapi import FastAPI

    app = env.client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(mode=mode)
    start(env.client)
    sheets_for(env.client)
    png = env.client.get(f"/api/demo/{S1}/sheets/3A-roll01.png").content
    r = env.client.post(f"/api/demo/{S1}/read", files={"image": ("3A-roll01.png", png)})
    assert r.status_code == 503
    message = r.json()["detail"]["message"]
    assert words in message and "Auto-fill" in message and "type the answers" in message
    assert env.client.get(f"/api/demo/{S1}/reading-summary").json()["sheets_read_by_ai"] == 0
    assert env.client.get(f"/api/demo/session/{S1}").json()["ai_reads"] == 0


def test_the_cost_cap_stops_ai_reads_with_a_plain_message(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_AI_READS_PER_SESSION", "1")
    start(env.client)
    images = []
    for colour in ("white", "grey"):
        buf = io.BytesIO()
        Image.new("RGB", (300, 400), colour).save(buf, "PNG")
        images.append(buf.getvalue())
    env.fake.messages.replies.extend([truth_read(1)])
    assert (
        env.client.post(f"/api/demo/{S1}/read", files={"image": ("a.png", images[0])}).status_code
        == 200
    )
    capped = env.client.post(f"/api/demo/{S1}/read", files={"image": ("b.png", images[1])})
    assert capped.status_code == 429 and "AI reads" in capped.json()["detail"]["message"]


def counts() -> dict[str, Any]:
    p = scenario.truth_profile(scenario.build_class(scenario.load_scenario()))
    return {"counts": {k.value: v for k, v in p.counts.items()}, "checked": p.children_checked}


def test_the_other_classes_and_the_cohorts_come_from_the_real_code(env: Env) -> None:
    start(env.client)
    assert env.client.get(f"/api/demo/{S1}/cohorts").status_code == 409
    plan = env.client.post(f"/api/demo/{S1}/simulate-classes", json=counts()).json()
    assert plan["simulated"] and len(plan["cohorts"]) == 3
    assert sum(c["includes_you"] for c in plan["cohorts"]) == 1
    dash = env.client.get(f"/api/demo/{S1}/dashboard").json()
    assert dash["simulated"] and all(
        r["classes"] is None or r["classes"] >= 5 for r in dash["cohorts"] + dash["by_error"]
    )


def test_the_post_test_gives_rows_on_form_b_and_cohort_before_and_after(env: Env) -> None:
    start(env.client)
    env.client.post(f"/api/demo/{S1}/simulate-classes", json=counts())
    post = env.client.post(f"/api/demo/{S1}/post-test").json()
    assert post["form"] == "B" and len(post["rows"]) == 20 and post["simulated"]
    dash = env.client.get(f"/api/demo/{S1}/dashboard").json()
    assert dash["before_after"] and all(
        r["classes"] is None or r["classes"] >= 5 for r in dash["before_after"]
    )


def test_the_chat_waits_for_a_person_when_the_ai_has_no_draft(env: Env) -> None:
    start(env.client)
    env.client.post(f"/api/demo/{S1}/simulate-classes", json=counts())
    view = env.client.post(
        f"/api/demo/{S1}/chat/ask", json={"text": "How do I teach taking away with borrowing?"}
    ).json()
    assert view["wait_seconds"] == 60 and len(view["questions"]) == 1
    skipped = env.client.post(f"/api/demo/{S1}/chat/skip").json()
    q = skipped["questions"][0]
    assert not [a for a in q["answers"] if a.get("author_role") == "ai"]


def test_the_coach_queue_holds_the_mentor_card_and_the_coach_decides(env: Env) -> None:
    start(env.client)
    env.client.post(f"/api/demo/{S1}/simulate-classes", json=counts())
    seeded = env.client.post(f"/api/demo/{S1}/coach/seed")
    assert seeded.status_code == 200, seeded.text
    assert "mentor_card" in seeded.json(), seeded.text[:600]
    view = seeded.json()
    assert view["simulated"] and view["mentor_card"]["status"] == "awaiting_coach"
    assert "Simulated mentor" in view["mentor_card"]["mentor_label"]
    dash = env.client.get(f"/api/demo/{S1}/dashboard").json()
    assert dash["approvals_pending"] >= 1
    done = env.client.post(f"/api/demo/{S1}/coach/mentor-card", json={"decision": "approve"})
    assert done.status_code == 200, done.text
    assert done.json()["mentor_card"]["status"] == "approved"


def test_the_first_audio_is_labelled_pre_approved_and_falls_back_to_text_by_code(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    start(env.client)
    env.client.post(f"/api/demo/{S1}/simulate-classes", json=counts())
    out = env.client.post(f"/api/demo/{S1}/audio", json={}).json()
    assert out["badge"] == "Demo: pre-approved" and out["track"] == "sub-sfl.v1"
    assert out["source"] in ("ai", "template")
    assert "9 of 20" in out["script"] or out["source"] == "ai"
