# ruff: noqa: E501
"""Per-action cost and time: the cost sums, a missing price, exact totals under parallel calls, an action
that makes several Claude calls, speech calls and a background step, a second action that does not see the
first, and the ledger holding metadata only."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from services.api.db import Base, make_engine
from services.speech.provider import MockProvider
from services.speech.sarvam import SpeechError
from services.usage import context, meter, pricing, store
from services.usage.api import router, summarise
from services.usage.middleware import ActionMeterMiddleware
from services.usage.models import UsageAction, UsageEntry


@pytest.fixture()
def ledger(tmp_path: Path) -> Iterator[sessionmaker]:  # type: ignore[type-arg]
    engine = make_engine(f"sqlite:///{tmp_path / 'usage.sqlite'}")
    Base.metadata.create_all(engine)
    sqlite3.connect(tmp_path / "usage.sqlite").execute("PRAGMA journal_mode=WAL").close()
    factory = sessionmaker(engine, expire_on_commit=False)
    store.set_factory(factory)
    pricing.reset()
    yield factory
    store.set_factory(None)
    pricing.reset()


def _with_rate(monkeypatch: pytest.MonkeyPatch, rate: float | None) -> None:
    cfg = dict(pricing.config())
    cfg["inr_per_usd"] = rate
    monkeypatch.setattr(pricing, "config", lambda: cfg)


# --- cost per kind -----------------------------------------------------------------------------


def test_llm_cost_comes_from_the_model_price_and_a_missing_model_is_none():
    got = pricing.llm_cost(
        "claude-haiku-5-5",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read=0,
        cache_write=0,
    )
    assert got is not None and got > 0
    assert (
        pricing.llm_cost(
            "no-such-model", input_tokens=5, output_tokens=5, cache_read=0, cache_write=0
        )
        is None
    )


def test_speech_cost_converts_inr_at_the_configured_rate(monkeypatch: pytest.MonkeyPatch):
    _with_rate(monkeypatch, 80.0)
    inr = pricing.speech_cost("sarvam", "tts", characters=10_000)
    assert inr == pytest.approx(30.0 / 80.0)  # 30 INR per 10,000 characters at 80 INR to the USD


def test_a_missing_rate_or_provider_is_none_never_zero(monkeypatch: pytest.MonkeyPatch):
    _with_rate(monkeypatch, None)
    assert pricing.speech_cost("sarvam", "tts", characters=10_000) is None
    _with_rate(monkeypatch, 80.0)
    assert pricing.speech_cost("nobody", "tts", characters=10_000) is None


def test_cloud_run_cost_is_none_until_prices_are_filled_in(monkeypatch: pytest.MonkeyPatch):
    assert pricing.cloud_run_cost(2000) is None
    cfg = dict(pricing.config())
    cfg["cloud_run"] = {
        **cfg["cloud_run"],
        "price_per_vcpu_second_usd": 0.00002,
        "price_per_gib_second_usd": 0.000002,
    }
    monkeypatch.setattr(pricing, "config", lambda: cfg)
    # 2 s x (1 vCPU x 0.00002 + 1 GiB x 0.000002)
    assert pricing.cloud_run_cost(2000) == pytest.approx(2 * (0.00002 + 0.000002))


# --- totals --------------------------------------------------------------------------------------


def _entry(
    kind: str, units: dict, cost: float | None, ms: int = 100, status: str = "ok"
) -> UsageEntry:  # type: ignore[type-arg]
    from datetime import UTC, datetime

    return UsageEntry(
        action_id="a" * 12, kind=kind, provider="p", units=units, cost_usd=cost,
        started_at=datetime.now(UTC), duration_ms=ms, status=status, meta={},
    )  # fmt: skip


def test_totals_count_failed_and_retried_calls_and_flag_missing_prices():
    action = UsageAction(id="a" * 12, name="x", inflight=0)
    got = summarise(
        action,
        [
            _entry("llm", {"input_tokens": 10, "output_tokens": 5}, 0.01),
            _entry("llm", {"input_tokens": 20, "output_tokens": 5}, 0.02, status="retried"),
            _entry("tts", {"characters": 100}, None, status="failed"),
            _entry("tts", {"characters": 200}, 0.003),
        ],
    )
    assert got["by_kind"]["llm"]["calls"] == 2 and got["by_kind"]["llm"]["retried"] == 1
    assert got["by_kind"]["llm"]["input_tokens"] == 30
    assert got["by_kind"]["tts"]["failed"] == 1 and got["by_kind"]["tts"]["characters"] == 300
    assert got["by_kind"]["tts"]["priced"] is False  # one line has no price: n/a, not 0
    assert got["totals"]["cost_usd"] == pytest.approx(0.033) and got["totals"]["priced"] is False
    assert got["complete"] is True


# --- parallel calls are not lost --------------------------------------------------------------------


def test_parallel_calls_under_one_action_are_all_counted(ledger):  # type: ignore[no-untyped-def]
    tokens = context.enter("action-parallel-1", "t")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [
                context.submit(
                    pool, meter.record, "tts", "bodhan",
                    model_or_voice="Kavya", units={"characters": n}, cost_usd=0.001, duration_ms=10,
                )
                for n in range(1, 61)
            ]  # fmt: skip
            for f in futures:
                f.result()
    finally:
        context.leave(tokens)
    with ledger() as db:
        rows = list(db.query(UsageEntry).filter_by(action_id="action-parallel-1"))
    assert len(rows) == 60
    assert sum(r.units["characters"] for r in rows) == sum(range(1, 61))


def test_a_thread_without_the_context_records_nothing(ledger):  # type: ignore[no-untyped-def]
    tokens = context.enter("action-nocontext", "t")
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(
                meter.record, "tts", "bodhan", units={"characters": 5}
            ).result()  # plain submit
    finally:
        context.leave(tokens)
    with ledger() as db:
        assert db.query(UsageEntry).filter_by(action_id="action-nocontext").count() == 0


# --- an action over HTTP -----------------------------------------------------------------------------


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ActionMeterMiddleware)
    app.include_router(router)
    provider = meter.MeteredProvider(MockProvider("mock", max_input_chars=500))

    def late() -> None:
        meter.record("llm", "anthropic", model_or_voice="claude-haiku-5-5", units={"input_tokens": 7, "output_tokens": 3}, duration_ms=5)  # fmt: skip

    @app.post("/work")
    def work(background: BackgroundTasks) -> dict[str, bool]:
        for _ in range(3):
            meter.record_llm(
                {
                    "model": "claude-haiku-5-5",
                    "tokens_in": 100,
                    "tokens_out": 20,
                    "latency_ms": 50,
                    "call_key": "c1",
                }
            )
        for i in range(4):
            provider.synthesize("x" * (10 * (i + 1)), "en", "Kavya", None)
        background.add_task(late)
        return {"ok": True}

    return app


def test_an_action_with_several_claude_calls_speech_and_a_background_step(ledger):  # type: ignore[no-untyped-def]
    client = TestClient(_app())
    aid = "11111111-aaaa-bbbb-cccc-000000000001"
    assert (
        client.post(
            "/work", headers={"X-Action-Id": aid, "X-Action-Name": "download_audio"}
        ).status_code
        == 200
    )
    got = client.get(f"/api/actions/{aid}/usage").json()
    assert got["name"] == "download_audio" and got["complete"] is True
    assert got["by_kind"]["llm"]["calls"] == 4  # three in the request, one in the background step
    assert got["by_kind"]["llm"]["input_tokens"] == 307
    assert got["by_kind"]["tts"]["calls"] == 4 and got["by_kind"]["tts"]["characters"] == 100
    assert (
        got["by_kind"]["cloud_run"]["calls"] == 1
        and got["by_kind"]["cloud_run"]["estimated"] is True
    )
    assert got["by_kind"]["tts"]["priced"] is False  # the mock provider has no price: n/a
    assert got["time"]["calls_sum_ms"] >= got["time"]["calls_wall_ms"] >= 0


def test_complete_is_false_while_a_request_is_still_open_then_true(ledger):  # type: ignore[no-untyped-def]
    aid = "11111111-aaaa-bbbb-cccc-000000000002"
    client = TestClient(_app())
    with ledger() as db:
        store.open_action(db, aid, "slow")
    assert client.get(f"/api/actions/{aid}/usage").json()["complete"] is False
    with ledger() as db:
        store.close_action(db, aid)
    assert client.get(f"/api/actions/{aid}/usage").json()["complete"] is True


def test_a_second_action_does_not_include_the_first(ledger):  # type: ignore[no-untyped-def]
    client = TestClient(_app())
    first, second = "22222222-aaaa-bbbb-cccc-000000000001", "22222222-aaaa-bbbb-cccc-000000000002"
    client.post("/work", headers={"X-Action-Id": first, "X-Action-Name": "one"})
    client.post("/work", headers={"X-Action-Id": second, "X-Action-Name": "two"})
    a = client.get(f"/api/actions/{first}/usage").json()
    b = client.get(f"/api/actions/{second}/usage").json()
    assert a["by_kind"]["llm"]["calls"] == b["by_kind"]["llm"]["calls"] == 4
    assert a["name"] == "one" and b["name"] == "two"
    assert {e["request_id"] for e in a["entries"]}.isdisjoint(
        {e["request_id"] for e in b["entries"] if e["kind"] == "cloud_run"}
    )


def test_a_request_without_an_action_id_is_not_counted_and_an_unknown_id_is_404(ledger):  # type: ignore[no-untyped-def]
    client = TestClient(_app())
    client.post("/work")
    with ledger() as db:
        assert db.query(UsageEntry).count() == 0
    assert client.get("/api/actions/33333333-aaaa-bbbb-cccc-000000000009/usage").status_code == 404
    assert client.get("/api/actions/bad id/usage").status_code in (404, 422)


def test_a_failed_provider_call_is_recorded(ledger):  # type: ignore[no-untyped-def]
    provider = meter.MeteredProvider(MockProvider("mock", fail=SpeechError("rate", 429, "x")))
    tokens = context.enter("action-failed-1", "t")
    try:
        with pytest.raises(SpeechError):
            provider.synthesize("hello", "en", "Kavya", None)
    finally:
        context.leave(tokens)
    with ledger() as db:
        row = db.query(UsageEntry).filter_by(action_id="action-failed-1").one()
    assert row.status == "failed" and row.kind == "tts"


# --- metadata only ---------------------------------------------------------------------------------------


def test_the_ledger_has_no_column_that_could_hold_content(ledger):  # type: ignore[no-untyped-def]
    cols = {c["name"] for c in inspect(ledger().get_bind()).get_columns("usage_entries")}
    assert cols == {
        "id", "action_id", "kind", "provider", "model_or_voice", "units", "cost_usd",
        "started_at", "duration_ms", "status", "request_id", "meta",
    }  # fmt: skip


@pytest.mark.parametrize(
    ("kind", "units", "meta"),
    [
        ("tts", {"text": 5}, {}),
        ("llm", {"input_tokens": "a prompt"}, {}),
        ("llm", {"input_tokens": 1}, {"prompt": True}),
        ("stt", {"transcript": 1}, {}),
        ("llm", {"input_tokens": 1}, {"cached": "yes"}),
        ("chat", {}, {}),
    ],
)
def test_content_cannot_be_written(kind, units, meta, ledger):  # type: ignore[no-untyped-def]
    tokens = context.enter("action-privacy-1", "t")
    try:
        with pytest.raises(ValueError):
            meter.record(kind, "x", units=units, meta=meta)
    finally:
        context.leave(tokens)
