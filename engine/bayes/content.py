"""Loaders for the 32-state model's content files (content/bayes/), with validation.

The only module of engine/bayes that reads files. Everything else in the package is pure and takes
the loaded objects as arguments. Every value is a build default, not reviewed by an educator
(docs/BAYESIAN-MODEL.md).
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from engine.model import ErrorCode

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content" / "bayes"
LEGACY_MOVELISTS = ROOT / "content" / "movelists"
DEFAULT_PARAMS = CONTENT / "params.v1.yaml"
ENV_PARAMS = "BAYES_PARAMS"
PROVENANCE = "build default, not reviewed by an educator"
INF = math.inf

# name -> (lowest valid, highest valid, whole number)
RANGES: dict[str, tuple[float, float, bool]] = {
    "p_P0": (0, 1, False),
    "p_E0_P1": (0, 1, False),
    "p_E0_P0": (0, 1, False),
    "r_diag": (0, 1, False),
    "obs_W0": (0, 1, False),
    "g0": (0, 1, False),
    "g_PE": (0, 1, False),
    "slip": (0, 1, False),
    "c_none": (0, 1, False),
    "c_none_PE": (0, 1, False),
    "g_nm": (0, 1, False),
    "c_nm_easy": (0, 1, False),
    "delta0": (0, 1, False),
    "rho": (0, 1, False),
    "prime_window": (1, 40, True),
    "beta0": (-INF, INF, False),
    "beta_cov": (0, INF, False),
    "beta_fit": (0, INF, False),
    "beta_scaf": (0, INF, False),
    "beta_att": (0, INF, False),
    "beta_over": (0, INF, False),
    "fit_E_noP": (0, 1, False),
    "fit_W_noE": (0, 1, False),
    "gamma0": (-INF, INF, False),
    "gamma_conf": (0, INF, False),
    "gamma_E": (0, INF, False),
    "gamma_att": (0, INF, False),
    "shift_rate": (0, 1, False),
    "h0_P": (0, 1, False),
    "h0_E": (0, 1, False),
    "h0_W": (0, 1, False),
    "c0": (1e-9, INF, False),
    "tau": (1e-9, INF, False),
    "K_push": (0, INF, False),
    "addressed_bonus": (0, 1, False),
    "neglect": (0, 1, False),
    "neglect_after": (1, 40, True),
    "overload_drag": (0, 1, False),
    "ov_window": (1, 40, True),
    "ov_free": (0, 40, True),
    "heavy_cov": (0, 1, False),
}


@dataclass(frozen=True)
class Params:
    """Every numeric parameter (docs/BAYESIAN-MODEL.md section 4). Build defaults."""

    p_P0: float
    p_E0_P1: float
    p_E0_P0: float
    r_diag: float
    obs_W0: float
    g0: float
    g_PE: float
    slip: float
    c_none: float
    c_none_PE: float
    g_nm: float
    c_nm_easy: float
    delta0: float
    rho: float
    prime_window: int
    beta0: float
    beta_cov: float
    beta_fit: float
    beta_scaf: float
    beta_att: float
    beta_over: float
    fit_E_noP: float
    fit_W_noE: float
    gamma0: float
    gamma_conf: float
    gamma_E: float
    gamma_att: float
    shift_rate: float
    h0_P: float
    h0_E: float
    h0_W: float
    c0: float
    tau: float
    K_push: float
    addressed_bonus: float
    neglect: float
    neglect_after: int
    overload_drag: float
    ov_window: int
    ov_free: int
    heavy_cov: float

    def __post_init__(self) -> None:
        for f in fields(self):
            check_value(f.name, getattr(self, f.name))

    def as_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def with_values(self, **changes: float) -> Params:
        return params_from_dict({**self.as_dict(), **changes})


PARAM_NAMES: tuple[str, ...] = tuple(f.name for f in fields(Params))
if set(PARAM_NAMES) != set(RANGES):  # pragma: no cover - a build error, caught at import
    raise RuntimeError("Params and RANGES disagree")


def check_value(name: str, value: Any) -> None:
    if name not in RANGES:
        raise ValueError(f"unknown parameter {name!r}")
    lo, hi, whole = RANGES[name]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"parameter {name} must be a number, not {value!r}")
    if whole and float(value) != int(value):
        raise ValueError(f"parameter {name} must be a whole number of turns, not {value!r}")
    if not (lo <= value <= hi) or math.isnan(value):
        raise ValueError(f"parameter {name}={value} is outside its valid range [{lo}, {hi}]")


def params_from_dict(values: Mapping[str, float]) -> Params:
    missing = [n for n in PARAM_NAMES if n not in values]
    extra = [n for n in values if n not in PARAM_NAMES]
    if missing or extra:
        raise ValueError(f"parameters missing {missing} or unknown {extra}")
    kw: dict[str, Any] = {}
    for n in PARAM_NAMES:
        v = values[n]
        kw[n] = int(v) if RANGES[n][2] and float(v) == int(v) else v
    return Params(**kw)


@dataclass(frozen=True)
class ParamSet:
    """The defaults, each parameter's uncertainty band (low, high), and where they came from."""

    defaults: Params
    bands: Mapping[str, tuple[float, float]]
    provenance: Mapping[str, str]
    path: str


def load_params(path: str | Path | None = None) -> ParamSet:
    """Read and validate a parameter file: every parameter present, each default, low and high a
    valid value, and low <= default <= high. Raises ValueError saying what is wrong."""
    p = Path(path) if path is not None else DEFAULT_PARAMS
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{ENV_PARAMS}: cannot read {p}: {exc}") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("params"), dict):
        raise ValueError(f"{ENV_PARAMS}: {p} has no `params:` mapping")
    table: dict[str, Any] = raw["params"]
    defaults: dict[str, float] = {}
    bands: dict[str, tuple[float, float]] = {}
    prov: dict[str, str] = {}
    for name in PARAM_NAMES:
        entry = table.get(name)
        if not isinstance(entry, dict) or not {"default", "low", "high", "provenance"} <= set(
            entry
        ):
            raise ValueError(f"{ENV_PARAMS}: {p} needs {name}: {{default, low, high, provenance}}")
        for key in ("default", "low", "high"):
            check_value(name, entry[key])
        if not entry["low"] <= entry["default"] <= entry["high"]:
            raise ValueError(f"{ENV_PARAMS}: {name} needs low <= default <= high")
        defaults[name] = entry["default"]
        bands[name] = (float(entry["low"]), float(entry["high"]))
        prov[name] = str(entry["provenance"])
    extra = sorted(set(table) - set(PARAM_NAMES))
    if extra:
        raise ValueError(f"{ENV_PARAMS}: unknown parameters {extra} in {p}")
    return ParamSet(params_from_dict(defaults), bands, prov, str(p))


def params_path(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    raw = env.get(ENV_PARAMS, "").strip()
    return Path(raw) if raw else DEFAULT_PARAMS


# --- families


@dataclass(frozen=True)
class Family:
    name: str
    codes: tuple[ErrorCode, ...]
    meaning: Mapping[str, str]
    siblings: Mapping[ErrorCode, ErrorCode]
    shift: Mapping[ErrorCode, ErrorCode]


@dataclass(frozen=True)
class Families:
    by_name: Mapping[str, Family]

    def of(self, code: ErrorCode) -> Family:
        for f in self.by_name.values():
            if code in f.codes:
                return f
        raise ValueError(
            f"error code {code.value} is in no family (content/bayes/families.v1.yaml)"
        )


@lru_cache(maxsize=1)
def load_families() -> Families:
    raw = yaml.safe_load((CONTENT / "families.v1.yaml").read_text(encoding="utf-8"))
    out: dict[str, Family] = {}
    for name, f in raw["families"].items():
        codes = tuple(ErrorCode(c) for c in f["codes"])
        sib = {ErrorCode(a): ErrorCode(b) for a, b in (f.get("siblings") or {}).items()}
        shift = {ErrorCode(a): ErrorCode(b) for a, b in (f.get("shift") or {}).items()}
        for a, b in [*sib.items(), *shift.items()]:
            if a not in codes or b not in codes:
                raise ValueError(f"family {name}: {a.value} -> {b.value} leaves the family")
        if set(f["meaning"]) != {"place_value", "exchange", "written_step"}:
            raise ValueError(f"family {name}: meaning needs place_value, exchange, written_step")
        out[name] = Family(name, codes, dict(f["meaning"]), sib, shift)
    fams = Families(out)
    for code in ErrorCode:
        fams.of(code)  # every error code is mapped, or this raises
    return fams


# --- moves


@dataclass(frozen=True)
class MoveSpec:
    cov_P: float
    cov_E: float
    cov_W: float
    scaf: float
    conf: float
    demo: bool
    rule_drill: bool

    @property
    def max_cov(self) -> float:
        return max(self.cov_P, self.cov_E, self.cov_W)


NEUTRAL_MOVE = MoveSpec(0.0, 0.0, 0.0, 0.0, 0.0, False, False)


def legacy_move_ids() -> set[str]:
    ids: set[str] = set()
    for p in sorted(LEGACY_MOVELISTS.glob("*.yaml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        ids |= {m["id"] for m in raw["moves"]}
    return ids


@lru_cache(maxsize=1)
def load_moves() -> Mapping[str, MoveSpec]:
    raw = yaml.safe_load((CONTENT / "moves.v1.yaml").read_text(encoding="utf-8"))
    out: dict[str, MoveSpec] = {}
    for mid, m in raw["moves"].items():
        spec = MoveSpec(
            float(m["cov_P"]),
            float(m["cov_E"]),
            float(m["cov_W"]),
            float(m["scaf"]),
            float(m["conf"]),
            bool(m["demo"]),
            bool(m["rule_drill"]),
        )
        for k in ("cov_P", "cov_E", "cov_W", "scaf", "conf"):
            if not 0 <= getattr(spec, k) <= 1:
                raise ValueError(f"move {mid}: {k} must be in [0, 1]")
        out[mid] = spec
    missing = sorted(legacy_move_ids() - set(out))
    if missing:
        raise ValueError(f"content/bayes/moves.v1.yaml has no entry for legacy moves {missing}")
    return out


# --- note tags


@dataclass(frozen=True)
class Factor:
    variable: str
    value: int | str
    ratio: float
    families: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def load_note_tags() -> Mapping[str, tuple[Factor, ...]]:
    from engine.bayes.state import value_index

    raw = yaml.safe_load((CONTENT / "note_tags.v1.yaml").read_text(encoding="utf-8"))
    out: dict[str, tuple[Factor, ...]] = {}
    for tag, factors in raw["tags"].items():
        made = []
        for f in factors:
            value_index(f["variable"], f["value"])  # a known variable and value, or this raises
            if float(f["ratio"]) <= 0:
                raise ValueError(f"note tag {tag}: a ratio must be above 0")
            made.append(
                Factor(f["variable"], f["value"], float(f["ratio"]), tuple(f.get("families", ())))
            )
        out[tag] = tuple(made)
    return out


def check_tags(tags: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    known = load_note_tags()
    bad = [t for t in tags if t not in known]
    if bad:
        raise ValueError(f"unknown note tags {bad}; allowed: {sorted(known)}")
    return tuple(tags)


def validate_all(environ: Mapping[str, str] | None = None) -> ParamSet:
    """Everything the bayesian model needs at startup: the parameter file, families, moves, tags."""
    ps = load_params(params_path(environ))
    load_families()
    load_moves()
    load_note_tags()
    return ps
