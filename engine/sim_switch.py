"""The one switch between the two Practice Class child models.

SIMULATOR_MODEL = legacy | bayesian. Unset or empty means legacy; any other value is refused at
startup with a message. legacy is engine/simulator.py, unchanged (golden fixtures in
tests/fixtures/legacy_sim_golden.json). bayesian is the 32-state model in engine/bayes/, imported
lazily only when selected, with its parameter file from BAYES_PARAMS (default
content/bayes/params.v1.yaml), loaded and validated at startup only in bayesian mode.

A session records its model when it is created (the state's type carries it), so changing the
environment later cannot switch a running session.

Note: the one-variable "bayesian" model of the earlier build (engine/child_model.py) is superseded
and no longer selectable here; the legacy path always passes engine.child_model.LEGACY explicitly.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from engine.child_model import LEGACY
from engine.simulator import Problem, ScenarioConfig, Seat, SessionState, TurnPlan
from engine.simulator import new_session as legacy_new_session
from engine.simulator import plan_turn as legacy_plan_turn

ENV_MODEL = "SIMULATOR_MODEL"
MODELS = ("legacy", "bayesian")


def model_name(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    raw = env.get(ENV_MODEL, "").strip()
    if raw in ("", "legacy"):
        return "legacy"
    if raw == "bayesian":
        return "bayesian"
    raise ValueError(f"{ENV_MODEL} must be legacy or bayesian (or unset for legacy), not {raw!r}")


def check_startup(environ: Mapping[str, str] | None = None) -> str:
    """Called once when the API starts: a bad SIMULATOR_MODEL, or (in bayesian mode only) a bad
    parameter file or content file, stops the API here with a message."""
    name = model_name(environ)
    if name == "bayesian":
        from engine.bayes.content import validate_all

        validate_all(environ)
    return name


def new_session(
    config: ScenarioConfig,
    seats: Sequence[Seat],
    seed: int,
    *,
    model: str | None = None,
    note_tags: Sequence[str] = (),
    environ: Mapping[str, str] | None = None,
) -> Any:
    """A new session's state under the model SIMULATOR_MODEL names (or `model`). `note_tags` (the
    closed list in content/bayes/note_tags.v1.yaml) are soft evidence for the bayesian model; no
    screen sends them yet."""
    name = model_name(environ) if model is None else model
    if name not in MODELS:
        raise ValueError(f"unknown model {name!r}")
    if name == "legacy":
        if note_tags:
            raise ValueError("teacher-note tags need SIMULATOR_MODEL=bayesian")
        return legacy_new_session(config, seats, seed, LEGACY)
    from engine.bayes.content import load_params, params_path
    from engine.bayes.planner import new_session as bayes_new_session

    params = load_params(params_path(environ)).defaults
    return bayes_new_session(config, seats, seed, params, note_tags)


def model_of(state: Any) -> str:
    return "legacy" if isinstance(state, SessionState) else str(getattr(state, "model", "?"))


def plan_turn(
    state: Any,
    config: ScenarioConfig,
    move_id: str,
    *,
    addressed: str | None,
    posed: Problem | None,
) -> tuple[TurnPlan, Any, dict[str, Any] | None]:
    """One turn under the session's own model: (plan, next state, debug trace or None)."""
    if isinstance(state, SessionState):
        plan, nxt = legacy_plan_turn(state, config, move_id, addressed=addressed, posed=posed)
        return plan, nxt, None
    from engine.bayes.planner import plan_turn_traced

    return plan_turn_traced(state, config, move_id, addressed=addressed, posed=posed)


def state_to_dict(state: Any) -> dict[str, Any]:
    if isinstance(state, SessionState):
        from engine.simulator import state_to_dict as legacy_to_dict

        return legacy_to_dict(state)
    from engine.bayes.planner import to_dict

    return to_dict(state)


def state_from_dict(data: Mapping[str, Any]) -> Any:
    if data.get("model") == "bayesian":
        from engine.bayes.planner import from_dict

        return from_dict(data)
    from engine.simulator import state_from_dict as legacy_from_dict

    return legacy_from_dict(data)
