"""Practice Class content: Pydantic schemas, loaders, and the bridge to the engine's config.

Move lists, rubrics, scenarios, personas and child-line templates are data owned by Seema
(content/); code never hardcodes them. Each file is validated on load, and the cross-file
rules (a rubric only names moves that exist, a scenario only names real moves) are checked here.
The JSON Schemas in content/schemas/ are exported from these models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from engine.model import ErrorCode
from engine.simulator import (
    BEHAVIOURS,
    NEUTRAL,
    MoveEffect,
    Problem,
    ScenarioConfig,
    valid_problem,
)

CONTENT = Path(__file__).resolve().parents[2] / "content"
LANGS = ("en", "hi", "ta")


def _all_langs(v: dict[str, Any]) -> dict[str, Any]:
    missing = [lang for lang in LANGS if not v.get(lang)]
    if missing:
        raise ValueError(f"missing languages: {', '.join(missing)}")
    return v


class MoveDef(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z_]*$")
    behaviour: str
    strength: float = Field(ge=-1, le=1)  # change to error strength (negative lowers it)
    engagement: float = Field(ge=-1, le=1)
    quiet: bool = False
    label: dict[str, str]
    description: dict[str, str]
    examples: dict[str, list[str]]

    @field_validator("behaviour")
    @classmethod
    def _behaviour(cls, v: str) -> str:
        if v not in BEHAVIOURS:
            raise ValueError(f"behaviour must be one of {sorted(BEHAVIOURS)}")
        return v

    @field_validator("label", "description", "examples")
    @classmethod
    def _langs(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _all_langs(v)


class MoveList(BaseModel):
    error: ErrorCode
    version: int
    moves: list[MoveDef]

    @model_validator(mode="after")
    def _unique(self) -> MoveList:
        ids = [m.id for m in self.moves]
        if len(ids) != len(set(ids)):
            raise ValueError("move ids must be unique")
        if set(ids) & set(NEUTRAL):
            raise ValueError("'other' and 'off_task' are built in; do not define them")
        return self


class RubricPoint(BaseModel):
    id: str
    move_ids: list[str] = Field(min_length=1)
    text: dict[str, str]  # said as a strength
    try_next: dict[str, str]  # said as an idea to try

    @field_validator("text", "try_next")
    @classmethod
    def _langs(cls, v: dict[str, str]) -> dict[str, str]:
        return _all_langs(v)  # type: ignore[return-value]


class Rubric(BaseModel):
    error: ErrorCode
    version: int
    points: list[RubricPoint] = Field(min_length=3)

    @model_validator(mode="after")
    def _unique(self) -> Rubric:
        ids = [p.id for p in self.points]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric point ids must be unique")
        return self


class ProblemDef(BaseModel):
    kind: str
    a: int
    b: int = 0


class Scenario(BaseModel):
    error: ErrorCode
    version: int
    movelist: str
    rubric: str
    start_strength: float = Field(ge=0, le=1)
    start_engagement: float = Field(ge=0, le=1)
    max_turns: int = Field(ge=1, le=200)
    consecutive_correct_to_finish: int = Field(ge=1)
    quiet_turns: int = Field(ge=0)
    problems: list[ProblemDef] = Field(min_length=3)
    materials: list[str]
    material_moves: dict[str, str]
    seat_mix: dict[ErrorCode, int]

    @model_validator(mode="after")
    def _checks(self) -> Scenario:
        if self.error not in self.seat_mix:
            raise ValueError("seat_mix must include the scenario's own error")
        if not 1 <= sum(self.seat_mix.values()) <= 4:
            raise ValueError("seat_mix must seat 1 to 4 children with errors")
        for p in self.problems:
            if not valid_problem(Problem(p.kind, p.a, p.b)):  # type: ignore[arg-type]
                raise ValueError(f"invalid problem {p}")
        if set(self.material_moves) != set(self.materials):
            raise ValueError("material_moves must cover exactly the materials")
        return self


class PersonaChild(BaseModel):
    id: str
    gender: str
    temperament: str
    names: dict[str, str]

    @field_validator("names")
    @classmethod
    def _langs(cls, v: dict[str, str]) -> dict[str, str]:
        return _all_langs(v)  # type: ignore[return-value]


class PersonaFile(BaseModel):
    version: int
    children: list[PersonaChild] = Field(min_length=10)


class Templates(BaseModel):
    intents: dict[str, str]
    join: str
    and_: str = Field(alias="and")
    steps: dict[str, str]


@dataclass(frozen=True)
class LoadedScenario:
    scenario: Scenario
    movelist: MoveList
    rubric: Rubric
    config: ScenarioConfig


def _read(rel: str) -> Any:
    return yaml.safe_load((CONTENT / rel).read_text(encoding="utf-8"))


def slug(error: ErrorCode | str) -> str:
    return ErrorCode(error).value.lower()


@cache
def load_scenario(error: str) -> LoadedScenario:
    """Load and cross-check the scenario, move list and rubric for one error."""
    scenario = Scenario.model_validate(_read(f"scenarios/{slug(error)}.v1.yaml"))
    movelist = MoveList.model_validate(_read(f"movelists/{scenario.movelist}.yaml"))
    rubric = Rubric.model_validate(_read(f"rubrics/{scenario.rubric}.yaml"))
    ids = {m.id for m in movelist.moves}
    for point in rubric.points:
        unknown = set(point.move_ids) - ids
        if unknown:
            raise ValueError(f"rubric point {point.id} names unknown moves {sorted(unknown)}")
    for material, mid in scenario.material_moves.items():
        if mid not in ids and mid not in NEUTRAL:
            raise ValueError(f"material {material} maps to unknown move {mid}")
    config = ScenarioConfig(
        error=scenario.error,
        start_strength=scenario.start_strength,
        start_engagement=scenario.start_engagement,
        max_turns=scenario.max_turns,
        finish_streak=scenario.consecutive_correct_to_finish,
        quiet_turns=scenario.quiet_turns,
        problems=tuple(Problem(p.kind, p.a, p.b) for p in scenario.problems),  # type: ignore[arg-type]
        moves={
            m.id: MoveEffect(m.behaviour, m.strength, m.engagement, m.quiet) for m in movelist.moves
        },
        material_moves=dict(scenario.material_moves),
    )
    return LoadedScenario(scenario, movelist, rubric, config)


@cache
def load_personas() -> PersonaFile:
    return PersonaFile.model_validate(_read("personas/children.v1.yaml"))


@cache
def load_templates(lang: str) -> Templates:
    return Templates.model_validate(_read(f"templates/child_lines.{lang}.yaml"))


SCHEMAS: dict[str, type[BaseModel]] = {
    "movelist": MoveList,
    "rubric": Rubric,
    "scenario": Scenario,
    "personas": PersonaFile,
    "child_lines": Templates,
}


def schema_json(name: str) -> str:
    return (
        json.dumps(SCHEMAS[name].model_json_schema(by_alias=True), indent=2, sort_keys=True) + "\n"
    )
