"""How a simulated child's error strength changes: the legacy rule (default) or a Bayesian model.

`SIMULATOR_MODEL` picks one when a session is created (`model_from_env`); the session keeps it, so
changing the environment later cannot switch a running session. Both models expose the same three
steps to engine.simulator: `check` the scenario, `start` a child, and `learn` from a move.
Everything else (who speaks, the answer draw, the bug functions, stages, engagement, quiet, the
chorus, the end of a session) stays in engine.simulator and is the same for both.

legacy: strength starts at the scenario's start_strength and a move adds its fixed effect (scaled by
`overhear` for children it was not aimed at). Unchanged from before this module existed.

bayesian: Bayesian knowledge tracing with per-child uncertainty. Each child with an error holds a
belief b = P(she has repaired the misconception). b starts from a Beta prior whose mean is
1 - start_strength; a move with effect e teaches with probability T = LEARN_CAP * min(1, |e| / S),
scaled by her responsiveness r, so b <- b + (1 - b) * min(1, T * r) (times `overhear` when she only
overheard). The rest of the engine reads strength = P(wrong) = (1 - b)(1 - GUESS) + b * SLIP. The
prior and responsiveness come from generators of their own (seeded by session seed and seat), so the
per-turn generator makes exactly the draws it made under legacy. Spec: docs/BAYESIAN-MODEL.md.
Parameters are chosen defaults, not fitted to real children.

Pure Python. The only outside input is `model_from_env`, which reads the environment once per
session.
"""

from __future__ import annotations

import os
import random
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from engine.simulator import Child, ScenarioConfig

MODELS = ("legacy", "bayesian")
ENV_MODEL = "SIMULATOR_MODEL"
# .env names for the Bayesian parameters (BayesParams field -> variable).
ENV_PARAMS = {
    "prior_concentration": "BAYES_PRIOR_CONCENTRATION",
    "responsiveness_scale": "BAYES_RESPONSIVENESS_SCALE",
    "responsiveness_shape": "BAYES_RESPONSIVENESS_SHAPE",
    "learn_cap": "BAYES_LEARN_CAP",
    "effect_scale": "BAYES_EFFECT_SCALE",
    "guess": "BAYES_GUESS",
    "slip": "BAYES_SLIP",
}


def _unit(v: float) -> float:
    return round(min(1.0, max(0.0, v)), 9)


@dataclass(frozen=True)
class BayesParams:
    """Chosen defaults, not fitted to real children (docs/BAYESIAN-MODEL.md)."""

    prior_concentration: float = 20.0  # K: how tightly starting beliefs sit around their mean
    responsiveness_scale: float = 2.0  # r = scale * Beta(shape, shape): mean 1, range 0 to 2
    responsiveness_shape: float = 4.0
    learn_cap: float = 0.6  # T for the strongest move
    effect_scale: float | None = None  # S; None = the largest |effect| in the scenario's move list
    guess: float = 0.05  # P(right) for a child who still holds the misconception
    slip: float = 0.05  # P(wrong) for a child who has repaired it

    def __post_init__(self) -> None:
        if self.prior_concentration <= 0:
            raise ValueError("BAYES_PRIOR_CONCENTRATION must be above 0")
        if self.responsiveness_scale < 0 or self.responsiveness_shape <= 0:
            raise ValueError("BAYES_RESPONSIVENESS_SCALE must be 0 or more and SHAPE above 0")
        if not 0 <= self.learn_cap <= 1:
            raise ValueError("BAYES_LEARN_CAP must be between 0 and 1")
        if self.effect_scale is not None and self.effect_scale <= 0:
            raise ValueError("BAYES_EFFECT_SCALE must be above 0 (or unset)")
        if not (0 <= self.guess < 1 and 0 <= self.slip < 1 and self.guess + self.slip < 1):
            raise ValueError("BAYES_GUESS and BAYES_SLIP must be in [0, 1) and sum below 1")


class ChildModel(Protocol):
    @property
    def name(self) -> str: ...

    def check(self, config: ScenarioConfig) -> None: ...

    def start(self, child: Child, seat: int, seed: int, config: ScenarioConfig) -> Child: ...

    def learn(
        self, child: Child, effect: float, scale: float, config: ScenarioConfig
    ) -> tuple[float, float | None, float | None]:
        """(strength, belief, gain) after a move reaches her; belief and gain None under legacy."""
        ...

    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LegacyModel:
    """The rule-based model: strength falls by the move's fixed effect."""

    name: Literal["legacy"] = "legacy"

    def check(self, config: ScenarioConfig) -> None:
        return None

    def start(self, child: Child, seat: int, seed: int, config: ScenarioConfig) -> Child:
        return child

    def learn(
        self, child: Child, effect: float, scale: float, config: ScenarioConfig
    ) -> tuple[float, float | None, float | None]:
        return _unit(child.strength + effect * scale), None, None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name}


@dataclass(frozen=True)
class BayesianModel:
    """Bayesian knowledge tracing with a Beta prior and a per-child responsiveness."""

    params: BayesParams = field(default_factory=BayesParams)
    name: Literal["bayesian"] = "bayesian"

    def check(self, config: ScenarioConfig) -> None:
        up = sorted(m for m, e in config.moves.items() if e.strength > 0)
        if up:  # the model has no forgetting: a move that raises strength has no meaning here
            raise ValueError(
                f"the Bayesian child model cannot use moves that raise error strength: {up}"
            )

    def effect_scale(self, config: ScenarioConfig) -> float:
        if self.params.effect_scale is not None:
            return self.params.effect_scale
        return max((abs(e.strength) for e in config.moves.values()), default=0.0) or 1.0

    def learn_probability(self, effect: float, config: ScenarioConfig) -> float:
        """T for a move with this effect on strength: LEARN_CAP * min(1, |effect| / S)."""
        return round(self.params.learn_cap * min(1.0, abs(effect) / self.effect_scale(config)), 9)

    def derived_strength(self, belief: float) -> float:
        p = self.params
        return _unit((1 - belief) * (1 - p.guess) + belief * p.slip)

    def start(self, child: Child, seat: int, seed: int, config: ScenarioConfig) -> Child:
        if child.error is None:  # the correct child: strength 0, no belief, always right
            return child
        p = self.params
        a = p.prior_concentration * (1 - config.start_strength)
        c = p.prior_concentration * config.start_strength
        prior = random.Random(f"bayes-prior:{seed}:{seat}")
        b0 = 0.0 if a <= 0 else 1.0 if c <= 0 else prior.betavariate(a, c)
        resp = random.Random(f"bayes-resp:{seed}:{seat}")
        shape = p.responsiveness_shape
        r = p.responsiveness_scale * resp.betavariate(shape, shape)
        b0 = _unit(b0)
        return replace(
            child, strength=self.derived_strength(b0), belief=b0, responsiveness=r, last_gain=0.0
        )

    def gain(self, belief: float, responsiveness: float, t: float, scale: float) -> float:
        """The rise in belief: (1 - b) * min(1, T * r) for the child reached, `scale` times that
        for a child who overheard (so an overheard move gives exactly half at overhear 0.5)."""
        return (1 - belief) * min(1.0, t * responsiveness) * scale

    def learn(
        self, child: Child, effect: float, scale: float, config: ScenarioConfig
    ) -> tuple[float, float | None, float | None]:
        b = child.belief if child.belief is not None else 0.0
        r = child.responsiveness if child.responsiveness is not None else 1.0
        g = self.gain(b, r, self.learn_probability(effect, config), scale)
        belief = _unit(b + g)
        return self.derived_strength(belief), belief, g

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": asdict(self.params)}


LEGACY = LegacyModel()


def model_from_dict(data: Mapping[str, Any]) -> ChildModel:
    if data.get("name") == "bayesian":
        return BayesianModel(BayesParams(**data.get("params", {})))
    if data.get("name") in (None, "legacy"):
        return LEGACY
    raise ValueError(f"unknown child model {data.get('name')!r}")


def params_from_env(environ: Mapping[str, str]) -> BayesParams:
    values: dict[str, float] = {}
    for key, var in ENV_PARAMS.items():
        raw = environ.get(var, "").strip()
        if raw:
            try:
                values[key] = float(raw)
            except ValueError:
                raise ValueError(f"{var} must be a number, not {raw!r}") from None
    return BayesParams(**values)


def model_from_env(environ: Mapping[str, str] | None = None) -> ChildModel:
    """The one factory: SIMULATOR_MODEL = legacy | bayesian. Unset or empty = legacy; anything else
    is refused with a message saying what is allowed."""
    env = os.environ if environ is None else environ
    raw = env.get(ENV_MODEL, "").strip()
    if raw in ("", "legacy"):
        return LEGACY
    if raw == "bayesian":
        return BayesianModel(params_from_env(env))
    raise ValueError(f"{ENV_MODEL} must be legacy or bayesian (or unset for legacy), not {raw!r}")
