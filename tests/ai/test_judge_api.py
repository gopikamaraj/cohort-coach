from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai.audit import SqlAuditSink
from ai.client import CallContext, CallInput, run_call
from ai.registry import LAYERS
from ai.schemas import ChildLine
from services.api.judge import get_sink
from services.api.main import app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def api(sink: SqlAuditSink):  # type: ignore[no-untyped-def]
    app.dependency_overrides[get_sink] = lambda: sink
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ai_map_lists_all_calls_and_layers(api: TestClient) -> None:
    body = api.get("/api/judge/ai-map").json()
    assert body["layers"] == list(LAYERS)
    assert [c["id"] for c in body["calls"]] == [1, 2, 3, 4, 5, 6, 7, 8, 10]
    for call in body["calls"]:
        assert set(call["layers"]) == set(LAYERS)
        assert call["prompt_version"] >= 1 and call["model"].startswith("claude-")
        assert call["eval"]["bar"]


def test_audit_endpoint_is_metadata_only(api: TestClient, sink: SqlAuditSink) -> None:
    secret = "Ravi Kumar 9876543210 sticks"
    inp = CallInput(trusted={"engine_answer": 37}, untrusted={"teacher_text": secret})
    run_call(
        1,
        inp,
        context=CallContext(mode="recorded", sink=sink, fallback=lambda: ChildLine(text="x")),
    )
    body = api.get("/api/judge/audit?limit=5").json()
    assert body["count"] == 1
    row = body["calls"][0]
    assert row["call"] == "c01_child_voice" and row["fallback_used"] == "template:no_recording"
    assert set(row) >= {"tokens", "cost_usd", "latency_ms", "validators", "checker", "reviewer"}
    assert "Ravi" not in str(body) and "9876543210" not in str(body)


def test_audit_limit_is_bounded(api: TestClient) -> None:
    assert api.get("/api/judge/audit?limit=0").status_code == 422
    assert api.get("/api/judge/audit?limit=201").status_code == 422


def test_budget_summary_adds_costs_by_call_model_and_day(sink: SqlAuditSink) -> None:
    from scripts.budget import summarise

    for call, model, cost in [("c01_child_voice", "m1", 0.5), ("c01_child_voice", "m1", 0.25),
                              ("c07_checker", "m2", 0.1)]:  # fmt: skip
        sink.write(
            call_id=1, call_key=call, prompt_version=1, model=model, mode="live",
            cost_usd=cost, input_hash="a" * 64,
        )  # fmt: skip
    sums = summarise(sink.recent(100))
    assert sums["call"]["c01_child_voice"] == pytest.approx(0.75)
    assert sums["model"]["m2"] == pytest.approx(0.1)
    assert sum(sums["day"].values()) == pytest.approx(0.85)


def test_readme_where_ai_is_used_is_current() -> None:
    done = subprocess.run(
        [sys.executable, "scripts/readme.py", "--check"], cwd=ROOT, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in ("Child voices", "Output checker", "Answer reading"):
        assert name in readme
