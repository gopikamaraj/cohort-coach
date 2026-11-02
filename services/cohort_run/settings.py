"""The two cohort rules that a pilot or demo may relax, and where each value comes from.

Production reads the environment: `COHORT_MIN_CLASSES` (default 15, the engine's cohort size target)
and `COHORT_ALLOW_SINGLE_ITEM_PROBES` (default off: the 2-item rule always holds). A pilot or demo
run takes its values from its scenario file instead, and everything formed under a relaxed value
carries a label on screen (DECISIONS 2026-11-01).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from engine.grouping import COHORT_MIN

PILOT_COHORT_LABEL = "Pilot cohort, two classes"
SINGLE_ITEM_LABEL = "Based on one question per child"


@dataclass(frozen=True)
class CohortSettings:
    min_classes: int
    allow_single_item_probes: bool
    source: str  # "production" or "pilot_demo"

    @property
    def pilot_scale(self) -> bool:
        """Below the engine's cohort size: no waitlist split, the pilot's own comparison instead."""
        return self.min_classes < COHORT_MIN


def production() -> CohortSettings:
    raw = os.environ.get("COHORT_MIN_CLASSES", "").strip()
    n = int(raw) if raw.isdigit() and int(raw) >= 1 else COHORT_MIN
    single = os.environ.get("COHORT_ALLOW_SINGLE_ITEM_PROBES", "0").strip() == "1"
    return CohortSettings(n, single, "production")


def for_scenario(scenario: dict[str, Any]) -> CohortSettings:
    """A pilot or demo scenario names its own values; with none, production's apply."""
    s = scenario.get("settings") or {}
    if not s:
        return production()
    base = production()
    n = int(s.get("cohort_min_classes", base.min_classes))
    if n < 2:
        raise ValueError("a cohort needs at least two classes")
    return CohortSettings(n, bool(s.get("allow_single_item_probes", False)), "pilot_demo")


def cohort_label(n_classes: int, settings: CohortSettings) -> str | None:
    if not settings.pilot_scale:
        return None
    return PILOT_COHORT_LABEL if n_classes == 2 else f"Pilot cohort, {n_classes} classes"
