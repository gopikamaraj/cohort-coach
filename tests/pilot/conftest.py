"""Shared setup for the pilot tests: a pilot app on a temp database, in-memory stores with a clock
the tests can move, a stub speech service, and a stand-in for the models (no network, no spend)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from ai.audit import SqlAuditSink
from ai.client import CallContext
from ai.schemas import SheetRead
from engine.bugs import correct_answer, sub_sfl
from engine.forms import FORM_A
from services.api import practice as practice_api
from services.api.db import Base, PilotClassCount, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.pilot import auth, routes
from services.pilot.storage import LocalBlobStore, get_audio_store, get_sheets_store
from services.practice.stub_client import StubClient
from services.speech.service import SpeechService

SECRET = "test-secret-for-pilot-tokens"
ACCOUNTS = (
    "ops:coordinator:ops-key,seema:coordinator+coach:seema-key,"
    "rev:coach:rev-key,off:officer:off-key"
)


def _fake_join(
    clips: list[bytes], *, fmt: str = "m4a", kbps: int = 32, gap_s: float = 0.6
) -> tuple[bytes, float]:
    """A small file with the right container marker and a length from the clip count."""
    head = b"\x00\x00\x00\x18ftypM4A " if fmt == "m4a" else b"ID3\x03\x00"
    return head + b"x" * 2000 * len(clips), 20.0 * len(clips)


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


class ReadingClient:
    """Answers call 8 from a queue of sheets (in upload order) and everything else with the
    existing offline stand-in, which passes call 7."""

    def __init__(self) -> None:
        self.sheets: list[list[str]] = []
        self.confidence = 0.97
        self.reads = 0
        self.checks = 0
        self.fail_checks = False
        self.messages = SimpleNamespace(parse=self._parse)
        self._stub = StubClient()

    def queue(self, sheet: list[str], confidence: float | None = None) -> None:
        self.sheets.append(sheet)
        if confidence is not None:
            self.confidence = confidence

    def _parse(self, **kwargs: Any) -> Any:
        name = kwargs["output_format"].__name__
        if name == "SheetRead":
            self.reads += 1
            sheet = self.sheets.pop(0)
            out = SheetRead(reads=sheet, confidences=[self.confidence] * len(sheet))
            usage = SimpleNamespace(
                input_tokens=0,
                output_tokens=0,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            )
            return SimpleNamespace(parsed_output=out, usage=usage)
        if name == "Verdict":
            self.checks += 1
            if self.fail_checks:
                from ai.schemas import Verdict

                out = Verdict(
                    passed=False,
                    failed_items=["tone"],
                    reason_short="stub: tone",
                    reason_for_user="The tone is wrong.",
                )
                usage = SimpleNamespace(
                    input_tokens=0,
                    output_tokens=0,
                    cache_read_input_tokens=0,
                    cache_creation_input_tokens=0,
                )
                return SimpleNamespace(parsed_output=out, usage=usage)
        return self._stub.messages.parse(**kwargs)


@dataclass
class Env:
    client: TestClient
    factory: sessionmaker[Session]
    sheets: LocalBlobStore
    audio: LocalBlobStore
    clock: Clock
    models: ReadingClient
    speech: SpeechService
    tokens: dict[str, str] = field(default_factory=dict)

    def h(self, who: str = "seema") -> dict[str, str]:
        if who not in self.tokens:
            key = {"ops": "ops-key", "seema": "seema-key", "rev": "rev-key", "off": "off-key"}[who]
            res = self.client.post("/api/pilot/auth/signin", json={"name": who, "key": key})
            assert res.status_code == 200, res.text
            self.tokens[who] = res.json()["token"]
        return {"Authorization": f"Bearer {self.tokens[who]}"}


@pytest.fixture(autouse=True)
def _no_real_storage_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's .env may name real buckets; pilot tests choose their own storage."""
    for name in (
        "GCS_SHEETS_BUCKET",
        "GCS_AUDIO_BUCKET",
        "GCS_CREDENTIALS_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCS_SIGNER_SERVICE_ACCOUNT",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sink: SqlAuditSink,
    request: pytest.FixtureRequest,
) -> Iterator[Env]:
    monkeypatch.setenv("PILOT_MODE", "1")
    monkeypatch.setenv("PILOT_ACCOUNTS", ACCOUNTS)
    monkeypatch.setenv("PILOT_TOKEN_SECRET", SECRET)
    monkeypatch.setenv("PILOT_AUDIO_MAX", "10")
    monkeypatch.setenv("JUDGE_MODE", "0")
    monkeypatch.delenv("PILOT_AUDIO_FORMAT", raising=False)
    monkeypatch.delenv("PWA_ORIGIN", raising=False)
    # nothing the tests reject may be written into the repo's approved-rejections folder
    monkeypatch.setattr("ai.guard.rejections.APPROVED_DIR", tmp_path / "rejections")

    clock = Clock()
    auth.set_clock(clock)
    auth.reset_throttle()
    engine = make_engine(f"sqlite:///{tmp_path / 'pilot.sqlite'}")
    # SQLite ignores foreign keys unless asked; Postgres (production) does not. Ask, so a row that
    # points at one not yet written fails here and not on the live server.
    event.listen(engine, "connect", lambda con, _rec: con.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    sheets = LocalBlobStore(b"sheets-secret", clock=clock)
    audio = LocalBlobStore(b"audio-secret", clock=clock)
    models = ReadingClient()
    speech = SpeechService("stub")

    if request.node.get_closest_marker("real_audio") is None:
        # ffmpeg is slow on a laptop: stand in for the voice and the encoder unless a test asks
        speech.synthesize = lambda text, lang, voice: b"clip"  # type: ignore[method-assign]
        monkeypatch.setattr("services.pilot.audio.join_to_file", _fake_join)

    app = create_app(pilot=True)
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[routes.get_factory] = lambda: factory
    app.dependency_overrides[get_sheets_store] = lambda: sheets
    app.dependency_overrides[get_audio_store] = lambda: audio
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub", sink=sink, client=models
    )
    app.dependency_overrides[practice_api.get_speech] = lambda: speech
    yield Env(TestClient(app), factory, sheets, audio, clock, models, speech)
    auth.set_clock(__import__("time").time)
    auth.reset_throttle()


# ---- helpers the tests share ------------------------------------------------------------------

SCHOOL = {"school_code": "SCH-01", "class_code": "3A", "teacher_ref": "T-101"}


def init_body(data: bytes, **over: Any) -> dict[str, Any]:
    return {
        **SCHOOL,
        "consent_confirmed": True,
        "consent_ref": "HM-LETTER-2026-10",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mime": "image/jpeg",
        **over,
    }


def upload(
    env: Env, data: bytes, who: str = "ops", read: list[str] | None = None, **over: Any
) -> dict[str, Any]:
    """The whole upload as the phone does it: init, PUT to the signed URL, complete."""
    if read is not None:
        env.models.queue(read)
    res = env.client.post(
        "/api/pilot/sheets/init", json=init_body(data, **over), headers=env.h(who)
    )
    assert res.status_code == 200, res.text
    body = res.json()
    if body["duplicate"]:
        return body
    up = body["upload"]
    put = env.client.put(up["url"], content=data, headers=up["headers"])
    assert put.status_code == 200, put.text
    done = env.client.post(f"/api/pilot/sheets/{body['id']}/complete", headers=env.h(who))
    assert done.status_code == 200, done.text
    # the read runs in the background after the response; by now it has finished
    listed = env.client.get("/api/pilot/sheets", headers=env.h(who)).json()["sheets"]
    status = next(x["status"] for x in listed if x["id"] == body["id"])
    return {**body, **done.json(), "status": status}


def answers(sub_sfl_child: bool) -> list[str]:
    """One synthetic child's ten answers on Form A: correct, or SUB-SFL on the borrowing items."""
    row = [str(correct_answer(i)) for i in FORM_A.items]
    if sub_sfl_child:
        for i in FORM_A.items[6:10]:
            row[i.n - 1] = str(min(sub_sfl(i.a, i.b)))
    return row


def synthetic_class(n: int = 20, with_error: int = 12) -> list[list[str]]:
    return [answers(i < with_error) for i in range(n)]


def photo(i: int) -> bytes:
    """A distinct pretend JPEG per child (the models are stubbed; only the bytes differ)."""
    return b"\xff\xd8\xff" + f"sheet-{i}".encode() * 20


Seed = Callable[..., None]


@pytest.fixture
def seeded(env: Env) -> Env:
    """The counts 20 synthetic sheets add up to (12 children show SUB-SFL), written directly: the
    upload and read path has its own tests, and doing it 20 times per test is slow."""
    with env.factory() as db:
        db.add(
            PilotClassCount(
                school_code="SCH-01",
                class_code="3A",
                teacher_ref="T-101",
                children_checked=20,
                counts={"SUB-SFL": 12},
                anchor_wrong_count=0,
                untracked={},
            )
        )
        db.commit()
    return env
