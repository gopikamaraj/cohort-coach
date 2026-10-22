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
    assert [c["id"] for c in body["calls"]] == [1, 2, 3, 4, 5, 6, 7, 8, 10, 11]
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


def test_sample_sheets_are_recorded_reads_of_made_up_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "1")
    body = TestClient(app).get("/api/judge/sample-sheets").json()
    assert body["form"] == "A" and "recorded" in body["label"]
    assert len(body["children"]) >= 10 and all(len(r) == 10 for r in body["children"])
    assert body["unsure"] and all(0 <= b < 10 for boxes in body["unsure"].values() for b in boxes)
    assert not any("name" in str(k).lower() for k in body)  # no child is named
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert TestClient(app).get("/api/judge/sample-sheets").status_code == 403


def test_every_sample_row_is_a_form_a_row_with_no_check_item_text() -> None:
    from ai.validators.check_items import check_items

    body = TestClient(app).get("/api/judge/sample-sheets").json()
    assert check_items(body["label"] + body["note"]) == []


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("injection", "injection_marker"),
        ("harsh", "profanity"),
        ("phone", "pii_phone"),
        ("child_name", "pii_roster_name"),
    ],
)
def test_try_to_break_it_runs_the_prepared_line_through_the_real_prefilter(
    kind: str, code: str
) -> None:
    body = TestClient(app).post("/api/judge/try-break", json={"kind": kind}).json()
    assert body["blocked"] and code in body["codes"] and body["explanation"].startswith("Held back")
    assert body["line"]


def test_try_to_break_it_takes_no_free_text_and_speaks_her_language() -> None:
    client = TestClient(app)
    assert client.post("/api/judge/try-break", json={"kind": "anything else"}).status_code == 422
    hi = client.post("/api/judge/try-break", json={"kind": "phone", "language": "hi"}).json()
    assert hi["explanation"].startswith("रोका गया")
    assert (
        client.post("/api/judge/try-break", json={"kind": "phone", "language": "fr"}).status_code
        == 422
    )


def test_try_to_break_it_is_judge_mode_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert TestClient(app).post("/api/judge/try-break", json={"kind": "phone"}).status_code == 403


def test_the_injection_line_is_explained_as_an_instruction_not_as_a_rude_word() -> None:
    body = TestClient(app).post("/api/judge/try-break", json={"kind": "injection"}).json()
    assert "instruction to the system" in body["explanation"]
