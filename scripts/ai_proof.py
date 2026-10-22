"""One cheap live check per AI capability, written to docs/evidence/ai_usage_proof.json.

    python scripts/ai_proof.py [--yes] [--batch-wait 120] [--only caching citations ...]

Each check reports PASS, FAIL or SKIPPED (no key, no sample sheets, batch not finished): it never
fakes a pass. AI_USAGE.md may only say "Verified" for a capability whose key here shows PASS
(`tests/test_ai_usage_doc.py` enforces that). The checks:

  caching            two identical-prefix calls; the second shows cache_read_input_tokens > 0
  structured_output  calls 2, 7 and 8 parse into their Pydantic models with no retry
  citations          a call-4-shaped request returns citations that resolve to our sentence ids
                     (an API-level check: the product's call 4 arrives in P11), and the API
                     refuses citations together with structured output (the two-pass reason)
  batches            a 2-request Message Batch: batch id and final status
  image_input        call 8 on one synthetic sheet; the digits match the manifest truth

Prints a cost estimate first and asks before spending (--yes skips the question). Synthetic data
only: no real child, no real teacher.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai import config  # noqa: E402
from ai.calls.c02_move_label import label_move  # noqa: E402
from ai.calls.c07_checker import check_output  # noqa: E402
from ai.calls.c08_answer_reading import read_sheet  # noqa: E402
from ai.client import CallContext, LiveNotAllowed, _live_client  # noqa: E402
from engine.forms import PILOT_FORMS  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "ai_usage_proof.json"
SHEETS = ROOT / "data" / "synthetic_sheets"
ESTIMATE_USD = 0.10  # about 12 small calls; the batch is half price
ALL = ("caching", "structured_output", "citations", "batches", "image_input")

SENTENCES = [
    "I first ask the child to say her answer out loud.",
    "Then I show fifty-two as five bundles of ten and two loose sticks.",
    "I open one bundle so we have twelve loose sticks.",
    "At the end I ask her to add her answer back to check it.",
]
MOVES = [("ask_explain", "Asks the child to explain her steps"), ("show_bundles", "Uses bundles")]


def result(status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "detail": detail, **extra}


def live() -> CallContext:
    return CallContext(mode="live")


def check_caching() -> dict[str, Any]:
    args: dict[str, Any] = {
        "moves": MOVES, "children": ["Meena", "Ravi"], "language": "en", "context": live(),
    }  # fmt: skip
    first = label_move("Meena, show me with the bundles.", **args)
    second = label_move("Meena, show me with the bundles.", **args)
    assert first.run is not None and second.run is not None
    u1, u2 = first.run.usage, second.run.usage
    ok = u2.cache_read_tokens > 0
    return result(
        "PASS" if ok else "FAIL",
        "second call read the cached system prompt" if ok else "no cache read on the second call",
        model=second.run.model,
        first={"cache_write": u1.cache_write_tokens, "cache_read": u1.cache_read_tokens},
        second={"cache_write": u2.cache_write_tokens, "cache_read": u2.cache_read_tokens},
    )


def check_structured() -> dict[str, Any]:
    out: dict[str, Any] = {}
    label = label_move("Tell me how you got that.", moves=MOVES, children=["Meena"],
                       language="en", context=live())  # fmt: skip
    assert label.run is not None
    out["call_2"] = _clean(label.run)
    verdict = check_output(
        "Let us show it with sticks, Meena.", audience="child", language="en",
        target_error="SUB-SFL", code_checks=[], context=live(),
    )  # fmt: skip
    out["call_7"] = _clean(verdict.result)
    sheet = _first_sheet()
    if sheet is None:
        out["call_8"] = result(
            "SKIPPED", "no synthetic sheets (run scripts/make_synthetic_sheets.py)"
        )
    else:
        image, _truth = sheet
        outcome = read_sheet(image, "image/jpeg", PILOT_FORMS["A"], context=live())
        out["call_8"] = (
            result("FAIL", "no usable read")
            if outcome is None
            else _clean(outcome.runs[0], retried=outcome.retried)
        )
    states = [v["status"] for v in out.values()]
    status = "FAIL" if "FAIL" in states else "SKIPPED" if "SKIPPED" in states else "PASS"
    return result(status, "calls 2, 7 and 8 parsed into their models with no retry", **out)


def _clean(run: Any, retried: bool = False) -> dict[str, Any]:
    ok = run.fallback_used is None and run.retries == 0 and run.output is not None and not retried
    return result(
        "PASS" if ok else "FAIL",
        type(run.output).__name__ if run.output is not None else "no output",
        model=run.model,
        retries=run.retries,
        fallback=run.fallback_used,
    )


def _first_sheet() -> tuple[str, list[str]] | None:
    manifest = SHEETS / "manifest.json"
    path = SHEETS / "SIM_COV_H06.jpg"
    if not manifest.exists() or not path.exists():
        return None
    rec = next(r for r in json.loads(manifest.read_text(encoding="utf-8"))["sheets"]
               if r.get("hero_id") == "H06")  # fmt: skip
    truth = ["" if a["value"] is None else str(a["value"]) for a in rec["answers"]]
    return base64.b64encode(path.read_bytes()).decode(), truth


def check_image() -> dict[str, Any]:
    sheet = _first_sheet()
    if sheet is None:
        return result("SKIPPED", "no synthetic sheets (run scripts/make_synthetic_sheets.py)")
    image, truth = sheet
    outcome = read_sheet(image, "image/jpeg", PILOT_FORMS["A"], context=live())
    if outcome is None:
        return result("FAIL", "no usable read")
    sure = [(c.text, t) for c, t in zip(outcome.cells, truth, strict=True) if c.status == "ok"]
    wrong = [i + 1 for i, (got, want) in enumerate(sure) if got != want]
    ok = len(sure) >= 8 and not wrong
    return result(
        "PASS" if ok else "FAIL",
        f"{len(sure)} of 10 boxes read with confidence; {len(wrong)} of them differ from the truth",
        sheet="SIM_COV_H06.jpg",
        model=outcome.runs[-1].model,
        flagged_for_teacher=sum(1 for c in outcome.cells if c.status == "check"),
    )


def check_citations() -> dict[str, Any]:
    client = _live_client()
    model = config.model_for("MODEL_METHOD")
    doc = {
        "type": "document",
        "source": {"type": "content", "content": [{"type": "text", "text": s} for s in SENTENCES]},
        "title": "Mentor transcript (synthetic)",
        "citations": {"enabled": True},
        "cache_control": {"type": "ephemeral"},
    }
    ask = {"type": "text", "text": "List the method steps, one short sentence each, in the "
           "mentor's order. Say only what the transcript says."}  # fmt: skip
    resp = client.messages.create(
        model=model, max_tokens=500, messages=[{"role": "user", "content": [doc, ask]}]
    )
    cited: list[int] = []
    bad: list[str] = []
    for block in resp.content:
        for c in getattr(block, "citations", None) or []:
            if c.type != "content_block_location":
                bad.append(f"unexpected citation type {c.type}")
                continue
            for i in range(c.start_block_index, c.end_block_index):
                if not 0 <= i < len(SENTENCES):
                    bad.append(f"block {i} is not a sentence id")
                elif c.cited_text.strip() != SENTENCES[i]:
                    bad.append(f"cited text differs from sentence {i}")
                else:
                    cited.append(i)
    refused = _structured_refused(client, model, doc, ask)
    ok = bool(cited) and not bad
    return result(
        "PASS" if ok else "FAIL",
        f"{len(set(cited))} distinct sentence ids cited; all resolve"
        if ok
        else "; ".join(bad) or "no citations returned",
        model=model,
        sentence_ids=sorted(set(cited)),
        structured_output_with_citations_refused=refused,
    )


def _structured_refused(client: Any, model: str, doc: dict[str, Any], ask: dict[str, Any]) -> bool:
    """True when the API answers 400 to citations plus structured output (the documented rule)."""
    import anthropic

    steps = {"type": "array", "items": {"type": "string"}}
    schema = {
        "type": "object",
        "properties": {"steps": steps},
        "required": ["steps"],
        "additionalProperties": False,
    }
    try:
        client.messages.create(
            model=model, max_tokens=200,
            messages=[{"role": "user", "content": [doc, ask]}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )  # fmt: skip
    except anthropic.BadRequestError:
        return True
    return False


def check_batches(wait: int) -> dict[str, Any]:
    client = _live_client()
    model = config.model_for("MODEL_LABEL")
    previous = _previous_batch()
    if previous is not None:
        batch = client.messages.batches.retrieve(previous)
    else:
        reqs = [
            {"custom_id": f"proof-{i}", "params": {
                "model": model, "max_tokens": 20,
                "messages": [{"role": "user", "content": f"Reply with the number {i}."}],
            }}
            for i in (1, 2)
        ]  # fmt: skip
        batch = client.messages.batches.create(requests=reqs)
    deadline = time.time() + wait
    while batch.processing_status != "ended" and time.time() < deadline:
        time.sleep(5)
        batch = client.messages.batches.retrieve(batch.id)
    counts = batch.request_counts
    summary = {
        "batch_id": batch.id,
        "processing_status": batch.processing_status,
        "succeeded": counts.succeeded,
        "errored": counts.errored,
        "model": model,
    }
    if batch.processing_status != "ended":
        return result("SKIPPED", f"batch submitted, not finished in {wait} s; run again to resume",
                      **summary)  # fmt: skip
    ok = counts.succeeded == 2 and counts.errored == 0
    return result("PASS" if ok else "FAIL", "2-request batch ended", **summary)


def _previous_batch() -> str | None:
    """A batch from an earlier run that had not finished: resume it rather than pay again."""
    if not OUT.exists():
        return None
    old = json.loads(OUT.read_text(encoding="utf-8")).get("checks", {}).get("batches", {})
    return old.get("batch_id") if old.get("status") == "SKIPPED" else None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--batch-wait", type=int, default=120)
    ap.add_argument("--only", nargs="+", choices=ALL, default=list(ALL))
    args = ap.parse_args(argv)
    config.load_env()
    print(f"Estimated cost: about USD {ESTIMATE_USD:.2f} for {len(args.only)} checks (live calls).")
    if not args.yes and input("Run them? [y/N] ").strip().lower() != "y":
        print("Nothing run.")
        return 2
    runners = {
        "caching": check_caching,
        "structured_output": check_structured,
        "citations": check_citations,
        "batches": lambda: check_batches(args.batch_wait),
        "image_input": check_image,
    }
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"checks": {}}
    checks: dict[str, Any] = dict(old.get("checks", {}))
    for name in args.only:
        try:
            checks[name] = runners[name]()
        except LiveNotAllowed as exc:
            checks[name] = result("SKIPPED", str(exc))
        except Exception as exc:  # a failed check is recorded as FAIL, never hidden
            checks[name] = result("FAIL", f"{type(exc).__name__}: {str(exc)[:200]}")
        print(f"{name:18} {checks[name]['status']:8} {checks[name]['detail']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                "script": "scripts/ai_proof.py",
                "note": "Synthetic inputs only. Results as measured; not hand-edited.",
                "checks": checks,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 1 if any(c["status"] == "FAIL" for c in checks.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
