# ruff: noqa: E501
"""Cost of one billable event, from config only. A missing price gives None (shown as "n/a"), logs a
warning once, and is never turned into 0."""

from __future__ import annotations

import logging
from functools import cache
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)
CONFIG = Path(__file__).resolve().parents[2] / "content" / "usage_pricing.yaml"
_warned: set[str] = set()


@cache
def config() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return data


def reset() -> None:
    config.cache_clear()
    _warned.clear()


def _warn(key: str, what: str) -> None:
    if key not in _warned:
        _warned.add(key)
        log.warning("usage: no price for %s; its cost shows as n/a", what)


def llm_cost(
    model: str, *, input_tokens: int, output_tokens: int, cache_read: int, cache_write: int
) -> float | None:
    from ai.pricing import Usage, cost_usd

    try:
        return cost_usd(model, Usage(input_tokens, output_tokens, cache_read, cache_write))
    except KeyError:
        _warn(f"llm:{model}", f"model {model}")
        return None


def inr_to_usd(inr: float) -> float | None:
    rate = config().get("inr_per_usd")
    if not rate:
        _warn("inr_per_usd", "the INR to USD rate")
        return None
    return inr / float(rate)


def speech_cost(
    provider: str, function: str, *, characters: int = 0, seconds: float = 0.0
) -> float | None:
    from services.speech import costs

    entry = costs.prices()["providers"].get(provider, {}).get(function)
    if not entry or entry.get("price") is None:
        _warn(f"speech:{provider}:{function}", f"{provider} {function}")
        return None
    inr = costs.cost_inr(provider, function, seconds=seconds, chars=characters)
    return inr_to_usd(inr)


def cloud_run_cost(duration_ms: int) -> float | None:
    """An upper-bound estimate: the request's seconds times the service's vCPU and GiB at the
    configured prices, as if it had the instance to itself (instance-based billing is shared by
    concurrent requests)."""
    c = config()["cloud_run"]
    pv, pg = c.get("price_per_vcpu_second_usd"), c.get("price_per_gib_second_usd")
    if pv is None or pg is None:
        _warn("cloud_run", "Cloud Run vCPU and memory")
        return None
    seconds = duration_ms / 1000
    return seconds * (float(c["vcpu"]) * float(pv) + float(c["memory_gib"]) * float(pg))


def display() -> dict[str, Any]:
    c = config()
    return {"currency": c.get("display_currency", "USD"), "inr_per_usd": c.get("inr_per_usd")}
