# ruff: noqa: E501
"""A sample run of the per-action cost and time ledger, written to docs/build/reports/USAGE-SAMPLE.md.

It starts the real API in-process on a throwaway database with a scripted speech provider (no network, no
paid call), does "download audio" the way the app does (the action headers on the request), and "print
pack" (no billed call: only the requests the print makes), then reads each action's usage back and shows
the ledger entries and the footer text. Every number in the file comes from this run; prices stay as
configured, so a missing price shows n/a exactly as the footer would.

    python scripts/usage_sample.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JUDGE_MODE", "1")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from services.api import pack_audio as _pack  # noqa: E402,F401
from services.api.db import Base, make_engine  # noqa: E402
from services.api.main import create_app  # noqa: E402
from services.api.practice import get_speech  # noqa: E402
from services.api.profiles import get_session  # noqa: E402
from services.media.storage import get_audio_store  # noqa: E402
from services.speech import lessons  # noqa: E402
from services.usage import store as usage_store  # noqa: E402
from services.usage.meter import MeteredProvider  # noqa: E402
from tests.speech.test_lessons import Scripted, Speech, Store  # noqa: E402

HEAD = {"X-Role": "teacher", "X-User": "usage sample"}  # registered in main() before use
OUT = ROOT / "docs" / "build" / "reports" / "USAGE-SAMPLE.md"


def money(usd: float, display: dict) -> str:  # type: ignore[type-arg]
    if display["currency"] == "INR" and display["inr_per_usd"]:
        v = usd * display["inr_per_usd"]
        return f"₹{v:.3f}" if v < 1 else f"₹{v:.2f}"
    return f"${usd:.4f}" if usd < 1 else f"${usd:.2f}"


def total_text(u: dict) -> str:  # type: ignore[type-arg]
    if u["totals"]["priced"] and u["totals"]["entries"]:
        return money(u["totals"]["cost_usd"], u["display"])
    if u["totals"]["cost_usd"] > 0:
        return f"{money(u['totals']['cost_usd'], u['display'])} + n/a"
    return "n/a"


def seconds(ms: float) -> str:
    return f"{round(ms)} ms" if ms < 1000 else f"{ms / 1000:.1f} s"


def section(title: str, name: str, wall_ms: int, u: dict) -> str:  # type: ignore[type-arg]
    rows = "\n".join(
        f"| {e['kind']} | {e['provider']} | {e['model_or_voice'] or '—'} | "
        f"{', '.join(f'{k}={v}' for k, v in e['units'].items())} | "
        f"{'n/a' if e['cost_usd'] is None else e['cost_usd']} | {e['duration_ms']} ms | {e['status']} |"
        for e in u["entries"]
    )
    k = u["by_kind"]
    return (
        f"## {title}\n\n"
        f"Footer: `Last action: {name} | {seconds(wall_ms)} | {total_text(u)}`\n\n"
        f"Complete: {u['complete']} · wall (this run, measured at the client) {seconds(wall_ms)} · "
        f"calls added up {seconds(u['time']['calls_sum_ms'])} · calls together {seconds(u['time']['calls_wall_ms'])}\n\n"
        f"| Kind | Calls | Units | Cost |\n| --- | --- | --- | --- |\n"
        f"| Claude API | {k['llm']['calls']} | {k['llm']['input_tokens']:g} in, {k['llm']['output_tokens']:g} out | "
        f"{'—' if not k['llm']['calls'] else 'n/a' if not k['llm']['priced'] else k['llm']['cost_usd']} |\n"
        f"| Text to speech | {k['tts']['calls']} | {k['tts']['characters']:g} characters | "
        f"{'—' if not k['tts']['calls'] else 'n/a' if not k['tts']['priced'] else k['tts']['cost_usd']} |\n"
        f"| Speech to text | {k['stt']['calls']} | {k['stt']['seconds']:g} s of audio | "
        f"{'—' if not k['stt']['calls'] else 'n/a' if not k['stt']['priced'] else k['stt']['cost_usd']} |\n"
        f"| Cloud Run (est.) | {k['cloud_run']['calls']} | {k['cloud_run']['request_ms']:g} ms of request time"
        f"{', cold start' if k['cloud_run']['cold'] else ''} | "
        f"{'n/a' if not k['cloud_run']['priced'] else k['cloud_run']['cost_usd']} |\n\n"
        f"Ledger entries:\n\n| Kind | Provider | Model or voice | Units | Cost (USD) | Took | Status |\n"
        f"| --- | --- | --- | --- | --- | --- | --- |\n{rows}\n"
    )


def main() -> None:
    import time

    tmp = Path(tempfile.mkdtemp())
    engine = make_engine(f"sqlite:///{tmp / 'sample.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    usage_store.set_factory(factory)
    lessons.encode_mp3 = lambda wav, kbps: b"ID3" + wav[44:400]  # type: ignore[assignment]

    def session():  # type: ignore[no-untyped-def]
        with factory() as s:
            yield s

    speech, audio_store = Speech(Scripted("bodhan")), Store()
    chain = speech.chain  # type: ignore[attr-defined]
    chain.providers = {
        n: MeteredProvider(p) for n, p in chain.providers.items()
    }  # as default_chain does
    app = create_app()
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_speech] = lambda: speech
    app.dependency_overrides[get_audio_store] = lambda: audio_store
    client = TestClient(app)
    client.post("/api/users/register", json={"nickname": "usage sample"})

    # 1. Download audio: one request, the server writes the spoken script and voices it chunk by chunk
    a1 = "aaaaaaaa-0000-4000-8000-000000000001"
    t0 = time.perf_counter()
    r = client.post(
        "/api/audio/pack",
        json={
            "language": "en",
            "name": "Cohort-Coach-Intervention-PV-HEARD-en",
            "code": "PV-HEARD",
            "children": 3,
            "total": 16,
        },
        headers={**HEAD, "X-Action-Id": a1, "X-Action-Name": "download_audio"},
    )
    wall1 = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, r.text
    u1 = client.get(f"/api/actions/{a1}/usage").json()

    # 2. Print this pack: no billed call. The app fetches the paper's layout and the kept sheets, then prints.
    a2 = "bbbbbbbb-0000-4000-8000-000000000002"
    t0 = time.perf_counter()
    client.get("/api/health", headers={"X-Action-Id": a2, "X-Action-Name": "print_pack"})
    client.get(
        "/api/sheet-keep/status",
        headers={
            **HEAD,
            "X-Class-Id": "c-sample",
            "X-Action-Id": a2,
            "X-Action-Name": "print_pack",
        },
    )
    wall2 = int((time.perf_counter() - t0) * 1000)
    u2 = client.get(f"/api/actions/{a2}/usage").json()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "# Per-action cost and time: a sample run\n\n"
        "Generated by `python scripts/usage_sample.py` (the real API in-process, a scripted speech provider, "
        "a throwaway database, no network and no paid call). The numbers below come from that run. Prices are "
        "as configured in `content/usage_pricing.yaml` and `content/speech_prices.yaml`: the INR to USD rate "
        "and the Cloud Run prices are not filled in yet, so those lines show **n/a** here, exactly as the "
        "footer shows them. They are not zero.\n\n"
        + section("Download audio", "Download audio", wall1, u1)
        + "\n"
        + section("Print this pack", "Print this pack", wall2, u2)
        + "\nThe second action's table holds none of the first one's numbers: the footer starts again for each action.\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
