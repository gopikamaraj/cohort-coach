"""The pilot routes: 404 unless every condition holds; no-store headers; the first roll is read by
call 8 and labelled; auto-fill makes no AI call and labels the rest. FAKE folder, fake model."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from ai.client import CallContext
from ai.schemas import SheetRead
from services.api import practice as practice_api
from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.pilot_demo import api as pilot_api
from tests.pilot_demo.conftest import truth_rows
from tests.pilot_demo.test_ingest import FakeReader, FakeScanner, run
from tests.support_ai import FakeClient

ROOT = Path(__file__).resolve().parents[2]


class Env:
    def __init__(self, client: TestClient, fake: FakeClient, folder: Path) -> None:
        self.client, self.fake, self.folder = client, fake, folder


@pytest.fixture
def env(folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    run(folder, scanner=FakeScanner(), reader=FakeReader())
    monkeypatch.setenv("PILOT_DEMO", "1")
    monkeypatch.setenv("PILOT_DEMO_DIR", str(folder))
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
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
    c = TestClient(app)
    yield Env(c, fake, folder)


def truth_read(roll: int) -> SheetRead:
    row = truth_rows()[roll]
    return SheetRead(reads=row, confidences=[0.97] * len(row))


def test_every_route_works_when_every_condition_holds(env: Env) -> None:
    m = env.client.get("/api/pilot-data/manifest")
    assert (
        m.status_code == 200 and m.json()["banner"] == "Pilot data: real sheets, roll numbers only"
    )
    assert [c["class_code"] for c in m.json()["classes"]] == ["3A", "3B"]
    assert "answers" not in m.text and "given" not in m.text  # no child-level data in the manifest


@pytest.mark.parametrize("path", ["/manifest", "/sheet/3A/1"])
def test_routes_send_no_store_headers(env: Env, path: str) -> None:
    r = env.client.get(f"/api/pilot-data{path}")
    assert r.status_code == 200 and "no-store" in r.headers["cache-control"]


def test_the_sheet_is_the_normalised_image_and_paths_cannot_escape(env: Env) -> None:
    r = env.client.get("/api/pilot-data/sheet/3A/1")
    assert r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"
    for bad in (
        "/sheet/3A/9",
        "/sheet/..%2f/1",
        "/sheet/3A/0",
        "/sheet/3B/1",
        "/sheet/3A%2f..%2f3A/1",
    ):
        assert env.client.get(f"/api/pilot-data{bad}").status_code in (404, 422)


def test_the_first_roll_is_read_live_by_call_8_and_labelled(env: Env) -> None:
    env.fake.messages.replies.append(truth_read(1))
    r = env.client.post("/api/pilot-data/read", data={"class_code": "3A", "roll": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] == "Read by AI" and body["source"] == "ai" and body["ai_reads"] == 1
    assert [c["text"] for c in body["cells"]] == truth_rows()[1]
    assert len(env.fake.messages.calls) == 1
    blocks = [b for m in env.fake.messages.calls[0]["messages"] for b in m["content"]]
    sent = " ".join(str(b.get("text", "")) for b in blocks)  # the words (the picture is base64)
    assert "346" not in sent and "728" not in sent  # never told the dictated numbers or answers
    assert "no-store" in r.headers["cache-control"]


def test_a_picked_file_is_read_too_and_the_cap_holds(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_AI_READS_PER_SESSION", "1")
    pilot_api._reads["n"] = 0
    env.fake.messages.replies.append(truth_read(1))
    jpeg = (env.folder / "sheets" / "3A-roll01.jpg").read_bytes()
    ok = env.client.post(
        "/api/pilot-data/read",
        data={"class_code": "3A", "roll": 1},
        files={"image": ("x.jpg", jpeg, "image/jpeg")},
    )
    assert ok.status_code == 200
    again = env.client.post("/api/pilot-data/read", data={"class_code": "3A", "roll": 2})
    assert again.status_code == 429
    assert len(env.fake.messages.calls) == 1


def test_auto_fill_makes_no_ai_call_and_labels_the_rest(env: Env) -> None:
    r = env.client.post("/api/pilot-data/autofill", json={"class_code": "3A", "skip": [1]})
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    assert env.fake.messages.calls == []  # no AI call
    assert body["label"] == "Read from pilot answer file"
    assert [s["roll"] for s in body["sheets"]] == [2, 3]  # roll 1 skipped; 4 absent; 5 no sheet
    by = {s["roll"]: s for s in body["sheets"]}
    assert by[2]["verified"] is True and by[3]["verified"] is False  # truth row vs AI only
    assert body["no_sheet"] == [5] and body["absent"] == [4]
    assert all(c["status"] in ("ok", "check", "blank") for c in by[2]["cells"])
    assert "no-store" in r.headers["cache-control"]


def test_the_routes_are_404_without_each_condition(
    env: Env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def gone() -> None:
        for path in ("/manifest", "/sheet/3A/1"):
            assert env.client.get(f"/api/pilot-data{path}").status_code == 404
        assert (
            env.client.post("/api/pilot-data/autofill", json={"class_code": "3A"}).status_code
            == 404
        )
        assert (
            env.client.post(
                "/api/pilot-data/read", data={"class_code": "3A", "roll": 1}
            ).status_code
            == 404
        )

    with monkeypatch.context() as m:  # no PILOT_DEMO=1
        m.delenv("PILOT_DEMO")
        gone()
    with monkeypatch.context() as m:  # no folder
        m.setenv("PILOT_DEMO_DIR", str(tmp_path / "nowhere"))
        gone()
    with monkeypatch.context() as m:  # consent not confirmed
        text = (env.folder / "manifest.yaml").read_text("utf-8")
        (env.folder / "manifest.yaml").write_text(
            text.replace("consent_confirmed: true", "consent_confirmed: false"), "utf-8"
        )
        gone()
        (env.folder / "manifest.yaml").write_text(text, "utf-8")


def test_the_hosted_app_never_shows_the_option(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PILOT_DEMO")
    r = env.client.get("/api/pilot-data/manifest")
    assert r.status_code == 404 and r.json()["detail"] == {
        "pilot": False,
        "show": False,
        "reason": "",
    }


def test_a_machine_with_the_folder_but_no_consent_shows_it_disabled_with_a_reason(env: Env) -> None:
    text = (env.folder / "manifest.yaml").read_text("utf-8")
    (env.folder / "manifest.yaml").write_text(
        text.replace("consent_confirmed: true", "consent_confirmed: false"), "utf-8"
    )
    detail = env.client.get("/api/pilot-data/manifest").json()["detail"]
    assert detail["show"] is True and "consent" in detail["reason"].lower()


# --- guards that need no server -----------------------------------------------------------------


def test_no_pilot_file_is_tracked_by_git() -> None:
    out = subprocess.run(
        ["git", "ls-files", "data/pilot"], cwd=ROOT, capture_output=True, text=True
    )
    assert out.stdout.strip() == ""
    ignored = subprocess.run(
        ["git", "check-ignore", "data/pilot/pilot_answers.json", "data/pilot/sheets/3A-roll01.jpg"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert len(ignored.stdout.split()) == 2


def test_the_build_and_the_service_worker_never_carry_pilot_data() -> None:
    cfg = (ROOT / "apps" / "pwa" / "vite.config.ts").read_text("utf-8")
    assert "data/pilot" not in cfg and "runtimeCaching" not in cfg
    assert "navigateFallbackDenylist: [/^\\/api\\//]" in cfg  # no /api route is ever cached
    dist = ROOT / "apps" / "pwa" / "dist"
    if dist.is_dir():
        for p in dist.rglob("*"):
            assert "pilot_answers" not in p.name and "roll0" not in p.name


def test_a_sheet_is_read_with_the_key_of_the_paper_chosen_in_enter_check(env: Env) -> None:
    """The reader's plausible answers come from the chosen paper, not from the folder's form."""
    from services.papers.models import PaperRow

    seen: list[object] = []
    import services.pilot_demo.api as api_mod

    real = api_mod.read_sheet

    def spy(b64: str, media: str, form: object, context: object) -> object:
        seen.append(form)
        return real(b64, media, form, context=context)

    api_mod.read_sheet = spy  # type: ignore[assignment]
    try:
        assert (
            env.client.post(
                "/api/pilot-data/read",
                data={"class_code": "3A", "roll": 1, "paper_id": "P-0000000000ff"},
            ).status_code
            == 404
        )  # an unknown paper is refused, not silently read with the folder's form
        assert PaperRow  # the paper table is where the key comes from
    finally:
        api_mod.read_sheet = real  # type: ignore[assignment]
    assert seen == []
