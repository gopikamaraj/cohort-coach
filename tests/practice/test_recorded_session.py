"""Gate 1 in recorded mode: the SUB-SFL rehearsal recorded live on 2026-10-17
(scripts/practice_cli.py --record) replays here with no network, through the CLI, the library
and the API.

If you change a prompt, a validator input or the script, the hashes change and these tests say
"no_recording": re-record with
    AI_MODE=record python scripts/practice_cli.py --scenario sub-sfl --lang en --seed 5 --record \
        --script evals/sets/practice_scripts/sub-sfl-en.txt
Record only synthetic lines, never real teacher text.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient

from ai.audit import SqlAuditSink
from ai.client import FIXTURE_DIR, CallContext
from ai.validators.pii import check_pii
from services.api import practice as api
from services.api.judge import get_sink
from services.api.main import app
from services.practice.session import end_session, start_session, take_turn

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "evals/sets/practice_scripts/sub-sfl-en.txt"
LINES = SCRIPT.read_text(encoding="utf-8").splitlines()


def play(session, ctx):  # type: ignore[no-untyped-def]
    out = []
    for line in LINES:
        if line.startswith("/tap"):
            out.append(take_turn(session, material=line[5:].strip(), context=ctx))
        else:
            out.append(take_turn(session, text=line, context=ctx))
    return out


def test_the_recorded_rehearsal_replays_through_the_library(sink: SqlAuditSink) -> None:
    ctx = CallContext(mode="recorded", sink=sink)
    s = start_session("SUB-SFL", "en", seed=5)
    turns = play(s, ctx)
    assert len(turns) == 7
    assert all(t.layers["output"]["source"] == "ai" and t.badge == "checked" for t in turns), [
        t.layers["guardrails"]["fallback_used"] for t in turns
    ]  # a failure here usually means a missing recording: see the module docstring
    assert turns[0].label and turns[0].label["move_id"] == "pose_problem"
    assert [t.label["move_id"] for t in turns][:5] == [
        "pose_problem", "ask_explain", "show_bundles", "exchange_ten", "check_back",
    ]  # fmt: skip
    # Every number a child said was made by the engine.
    for t in turns:
        said = {int(x) for x in re.findall(r"\d+", t.child_text)}
        assert said <= set(t.numbers), (t.child_text, t.numbers)
    card, layers = end_session(s, context=ctx)
    assert card.source == "ai" and card.badge.value == "checked" and len(card.strengths) == 2
    for item in card.strengths:  # two verbatim quotes, each from her own turn
        her = next(r.teacher_text for r in s.records if r.turn == item.turn_id)
        assert item.quote in her
    assert layers["output"]["badge"] == "checked"


def test_the_recorded_rehearsal_replays_through_the_api(sink: SqlAuditSink) -> None:
    app.dependency_overrides[api.get_ai_context] = lambda: CallContext(mode="recorded", sink=sink)
    app.dependency_overrides[get_sink] = lambda: sink
    api._SESSIONS.clear()
    try:
        client = TestClient(app)
        created = client.post(
            "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": "en", "seed": 5}
        ).json()
        sid = created["session_id"]
        for line in LINES:
            body = {"material": line[5:].strip()} if line.startswith("/tap") else {"text": line}
            res = client.post(f"/api/practice/sessions/{sid}/turns", json=body)
            assert res.status_code == 200, res.text
            assert res.json()["badge"] == "checked"
        end = client.post(f"/api/practice/sessions/{sid}/end").json()
        assert len(end["card"]["strengths"]) == 2 and end["card"]["badge"] == "checked"
        assert len(end["transcript"]) == 7
    finally:
        app.dependency_overrides.clear()
        api._SESSIONS.clear()


def test_the_recorded_rehearsal_replays_through_the_cli() -> None:
    done = subprocess.run(
        [sys.executable, "scripts/practice_cli.py", "--scenario", "sub-sfl", "--lang", "en",
         "--seed", "5", "--recorded", "--script", str(SCRIPT)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "DATABASE_URL": "sqlite:///:memory:", "PYTHONIOENCODING": "utf-8",
             "PRACTICE_SKIP_CHECKER": "0", "PRACTICE_AI_INTENTS": "all"},  # not her .env
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert done.stdout.count("checked]") == 7  # one badge per turn
    assert "Feedback (private)" in done.stdout and "[checked" in done.stdout
    assert "you said:" in done.stdout


def fixture_files() -> Iterator[Path]:
    yield from FIXTURE_DIR.glob("*/*.json")


def test_recordings_are_synthetic_and_clean() -> None:
    files = list(fixture_files())
    assert len(files) >= 20
    secret = re.compile(r"sk-ant-|api[_-]?key|\b\d{9,}:[A-Za-z0-9_-]{20,}")
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert not secret.search(text), f.name
        data = json.loads(text)
        blob = json.dumps(data["outputs"], ensure_ascii=False)
        assert check_pii(blob) == [], f.name
