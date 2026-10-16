"""Cost from usage x prices in ai/pricing.yaml. Prices are data, never typed into code."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PRICING_PATH = Path(__file__).with_name("pricing.yaml")


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@lru_cache(maxsize=1)
def load_pricing() -> dict[str, object]:
    data = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pricing.yaml must be a mapping")
    for key in ("source_url", "as_of", "models"):
        if key not in data:
            raise ValueError(f"pricing.yaml is missing {key}")
    return data


def cost_usd(model: str, usage: Usage, *, batch: bool = False) -> float:
    data = load_pricing()
    models = data["models"]
    assert isinstance(models, dict)
    if model not in models:
        raise KeyError(f"no price for model {model!r} in ai/pricing.yaml")
    p = models[model]
    total = (
        usage.input_tokens * p["input"]
        + usage.cache_write_tokens * p["cache_write_5m"]
        + usage.cache_read_tokens * p["cache_read"]
        + usage.output_tokens * p["output"]
    ) / 1_000_000
    if batch:
        total *= float(data["batch_discount"])  # type: ignore[arg-type]
    return total
