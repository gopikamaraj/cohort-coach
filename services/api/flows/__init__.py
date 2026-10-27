"""The flow engine package: every teacher and mentor flow, defined once, for every channel."""

from __future__ import annotations

from services.api.flows.onboarding import ONBOARDING
from services.api.flows.steps import Flow
from services.api.flows.t1 import T1
from services.api.flows.t4 import T4, T6

FLOWS: dict[str, Flow] = {f.id: f for f in (ONBOARDING, T1, T4, T6)}
