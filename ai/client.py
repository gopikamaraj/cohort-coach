"""One path for every Claude call: `run_call`.

Renders the versioned prompt (stable system block first, cached), wraps untrusted text in tags,
parses a structured output, re-validates with Pydantic, runs the validators, retries within
bounds with the violations stated, falls back deterministically, checks the budget, and writes
one audit row.

Modes (AI_MODE): `recorded` reads ai/fixtures/recorded/<call>/<hash>.json (tests, CI, demos),
`live` calls the API, `record` calls the API and saves the answer as a fixture. With
ANTHROPIC_API_KEY unset the client refuses `live` and `record`.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pydantic
from pydantic import BaseModel

from ai import config
from ai.audit import SqlAuditSink, default_sink
from ai.pricing import Usage, cost_usd
from ai.prompt_loader import Prompt, load_prompt
from ai.registry import CallSpec, get_call
from ai.validators import ValidatorResult

log = logging.getLogger("ai.client")
FIXTURE_DIR = Path(__file__).with_name("fixtures") / "recorded"
_warned_cache: set[str] = set()

ValidatorFn = Callable[[BaseModel], list[ValidatorResult]]


class BudgetExceeded(RuntimeError):
    """Non-judge traffic is stopped by AI_BUDGET_USD_TOTAL or _DAILY; judge traffic by _HARD."""


class LiveNotAllowed(RuntimeError):
    """live and record modes need ANTHROPIC_API_KEY."""


@dataclass
class CallInput:
    """What the caller passes in. `untrusted` text is wrapped in tags and never obeyed."""

    trusted: dict[str, Any] = field(default_factory=dict)
    untrusted: dict[str, str] = field(default_factory=dict)  # tag name -> text
    images: list[tuple[str, str]] = field(default_factory=list)  # (media_type, base64)


@dataclass
class CallContext:
    judge: bool = False
    mode: str | None = None
    validators: ValidatorFn | None = None
    fallback: Callable[[], BaseModel] | None = None
    sink: SqlAuditSink | None = None
    client: Any = None  # anything with .messages.parse(...); tests pass a fake
    model: str | None = None  # override (call 8 retry uses MODEL_READ_RETRY)
    extra_system: str = ""  # appended after the cached prompt, e.g. rejected-before examples
    output_model: type[BaseModel] | None = None  # narrower schema, e.g. a move list as an enum


@dataclass
class CallResult:
    output: BaseModel | None
    fallback_used: str | None
    retries: int
    results: list[ValidatorResult]
    usage: Usage
    cost_usd: float
    latency_ms: int
    audit_id: int
    mode: str
    model: str
    prompt_version: int
    input_hash: str

    @property
    def ok(self) -> bool:
        return self.fallback_used is None and self.output is not None


def _wrap(tag: str, text: str) -> str:
    # A closing tag inside the text must not be able to end the wrapper.
    safe = text.replace("</", "<​/")
    return f"<{tag}>\n{safe}\n</{tag}>"


def render_user_content(inp: CallInput, retry_note: str = "") -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [
        {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}
        for mt, data in inp.images
    ]
    text = _wrap("facts", json.dumps(inp.trusted, ensure_ascii=False, sort_keys=True))
    for tag in sorted(inp.untrusted):
        text += "\n" + _wrap(tag, inp.untrusted[tag])
    if retry_note:
        text += f"\n\nYour last answer broke these rules: {retry_note}. Fix them."
    parts.append({"type": "text", "text": text})
    return parts


def input_hash(
    spec: CallSpec, prompt: Prompt, model: str, inp: CallInput, extra_system: str = ""
) -> str:
    blob = json.dumps(
        {
            "call": spec.key,
            "prompt_version": prompt.version,
            "model": model,
            "extra_system": extra_system,
            "trusted": inp.trusted,
            "untrusted": inp.untrusted,
            "images": [(mt, hashlib.sha256(d.encode()).hexdigest()) for mt, d in inp.images],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    salt = os.environ.get("AUDIT_HASH_SALT", "")
    if salt:  # a keyed hash, so a short or guessable input cannot be checked against the log
        return hmac.new(salt.encode(), blob.encode(), hashlib.sha256).hexdigest()
    return hashlib.sha256(blob.encode()).hexdigest()


def fixture_path(spec: CallSpec, digest: str) -> Path:
    return FIXTURE_DIR / spec.key / f"{digest[:16]}.json"


def _read_fixture(spec: CallSpec, digest: str) -> dict[str, Any] | None:
    path = fixture_path(spec, digest)
    if not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _usage_from_response(resp: Any) -> Usage:
    u = resp.usage
    return Usage(
        input_tokens=int(u.input_tokens or 0),
        output_tokens=int(u.output_tokens or 0),
        cache_read_tokens=int(getattr(u, "cache_read_input_tokens", 0) or 0),
        cache_write_tokens=int(getattr(u, "cache_creation_input_tokens", 0) or 0),
    )


@functools.cache
def _client_for(api_key: str) -> Any:
    import anthropic

    # We own retries so each is audited. One client per key keeps the connection pool (and its
    # TLS session) open between calls instead of paying a new handshake on every call.
    return anthropic.Anthropic(api_key=api_key, max_retries=0)


def _live_client() -> Any:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LiveNotAllowed("ANTHROPIC_API_KEY is not set; live and record modes are refused")
    return _client_for(key)


def check_budget(sink: SqlAuditSink, *, judge: bool) -> None:
    total = sink.spend_total()
    if judge:
        if total >= config.budget_hard_usd():
            raise BudgetExceeded("hard budget ceiling reached")
        return
    if sink.spend_total(judge=False) >= config.budget_total_usd():
        raise BudgetExceeded("total AI budget reached")
    if sink.spend_day(datetime.now(UTC).date(), judge=False) >= config.budget_daily_usd():
        raise BudgetExceeded("daily AI budget reached")


def _sum_usage(a: Usage, b: Usage) -> Usage:
    return Usage(
        a.input_tokens + b.input_tokens,
        a.output_tokens + b.output_tokens,
        a.cache_read_tokens + b.cache_read_tokens,
        a.cache_write_tokens + b.cache_write_tokens,
    )


def run_call(
    call: int | str, payload: CallInput, *, context: CallContext | None = None
) -> CallResult:
    ctx = context or CallContext()
    spec = get_call(call)
    policy = config.POLICIES[spec.key]
    prompt = load_prompt(spec.key)
    out_model = ctx.output_model or spec.output_model
    model = ctx.model or spec.model
    mode = ctx.mode or config.ai_mode()
    sink = ctx.sink or default_sink()
    digest = input_hash(spec, prompt, model, payload, ctx.extra_system)

    client = None
    if mode == "stub":  # a rule-based stand-in for the model: offline demos and tests, no spend
        if ctx.client is None:
            raise ValueError("stub mode needs a client")
        client = ctx.client
    elif mode in ("live", "record"):
        client = ctx.client or _live_client()
        check_budget(sink, judge=ctx.judge)

    started = time.monotonic()
    usage = Usage()
    outputs: list[dict[str, Any]] = []
    results: list[ValidatorResult] = []
    retries = 0
    output: BaseModel | None = None
    reason = "validators"
    retry_note = ""
    fixture = _read_fixture(spec, digest) if mode == "recorded" else None
    if mode == "recorded" and fixture is None:
        reason = "no_recording"

    attempts = 0 if (mode == "recorded" and fixture is None) else policy.max_retries + 1
    for attempt in range(attempts):
        retries = attempt
        parsed: BaseModel | None = None
        try:
            if mode == "recorded":
                assert fixture is not None
                outs = fixture.get("outputs") or [fixture["output"]]
                raw = outs[min(attempt, len(outs) - 1)]
                parsed = out_model.model_validate(raw)
                usage = _sum_usage(usage, Usage(**fixture.get("usage", {})))
            else:
                system = [
                    {"type": "text", "text": prompt.body, "cache_control": {"type": "ephemeral"}}
                ]
                if ctx.extra_system:
                    system.append({"type": "text", "text": ctx.extra_system})
                resp = client.messages.parse(
                    model=model,
                    max_tokens=policy.max_tokens,
                    system=system,
                    messages=[
                        {"role": "user", "content": render_user_content(payload, retry_note)}
                    ],
                    output_format=out_model,
                    output_config={"effort": policy.effort},
                    **(
                        {"thinking": think}
                        if (think := config.thinking_param(model, policy))
                        else {}
                    ),
                    timeout=policy.timeout_s,
                )
                usage = _sum_usage(usage, _usage_from_response(resp))
                if resp.parsed_output is None:
                    reason = "no_output"
                    continue
                # Re-validate with Pydantic regardless of what the SDK parsed.
                parsed = out_model.model_validate(resp.parsed_output.model_dump())
        except pydantic.ValidationError:
            reason = "schema"
            retry_note = "the answer did not match the required format"
            continue
        except LiveNotAllowed:
            raise
        except Exception as exc:  # API, timeout, connection: never hang, fall back
            reason = "api_error"
            log.warning("call %s attempt %d failed: %s", spec.key, attempt, type(exc).__name__)
            continue

        results = ctx.validators(parsed) if ctx.validators else []
        bad = [r for r in results if not r.ok]
        if not bad:
            output = parsed
            outputs.append(parsed.model_dump())
            break
        reason = "validators"
        retry_note = "; ".join(f"{r.name}: {', '.join(r.codes)}" for r in bad)

    fallback_used: str | None = None
    if output is None:
        if ctx.fallback is not None:
            output = ctx.fallback()
            fallback_used = f"template:{reason}"
        else:
            fallback_used = f"needs_human:{reason}"

    if mode == "record" and outputs and fallback_used is None:
        path = fixture_path(spec, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "call": spec.key,
                    "prompt_version": prompt.version,
                    "model": model,
                    "outputs": outputs,
                    "usage": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cache_read_tokens": usage.cache_read_tokens,
                        "cache_write_tokens": usage.cache_write_tokens,
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    if (
        mode in ("live", "record")
        and usage.cache_read_tokens == 0
        and spec.key not in _warned_cache
    ):
        _warned_cache.add(spec.key)
        log.warning(
            "call %s: cache_read_input_tokens is 0 (cache write %d); expected after the first call",
            spec.key,
            usage.cache_write_tokens,
        )

    cost = cost_usd(model, usage) if mode in ("live", "record") else 0.0  # replays spend nothing
    latency_ms = int((time.monotonic() - started) * 1000)
    audit_id = sink.write(
        call_id=spec.id,
        call_key=spec.key,
        prompt_version=prompt.version,
        model=model,
        mode=mode,
        judge=ctx.judge,
        metadata_only=spec.metadata_only,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        tokens_cache_read=usage.cache_read_tokens,
        tokens_cache_write=usage.cache_write_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
        validator_results=[{"name": r.name, "ok": r.ok, "codes": r.codes} for r in results],
        checker_verdict=None,
        checker_reason=None,
        retries=retries,
        fallback_used=fallback_used,
        input_hash=digest,
    )
    return CallResult(
        output=output,
        fallback_used=fallback_used,
        retries=retries,
        results=results,
        usage=usage,
        cost_usd=cost,
        latency_ms=latency_ms,
        audit_id=audit_id,
        mode=mode,
        model=model,
        prompt_version=prompt.version,
        input_hash=digest,
    )
