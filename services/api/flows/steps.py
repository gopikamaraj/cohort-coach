"""Steps: what a flow asks or says, independent of any channel.

A step names copy by string key and carries slot values; a channel adapter renders it. Step types:
message, choice, photo_batch, number_grid, voice, media, link. This module imports nothing from a
channel, the engine or the AI layer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

Kind = Literal["message", "choice", "photo_batch", "number_grid", "voice", "media", "link"]


class Option(BaseModel):
    id: str
    copy: str  # string key of the label


class LinkSpec(BaseModel):
    kind: Literal["practice", "web"]
    label_copy: str
    url: str | None = None


class Line(BaseModel):
    copy: str
    params: dict[str, str | int] = Field(default_factory=dict)


class Step(BaseModel):
    kind: Kind
    id: str
    copy: str
    params: dict[str, str | int] = Field(default_factory=dict)
    options: list[Option] = Field(default_factory=list)
    lines: list[Line] = Field(default_factory=list)  # extra lines under the main text
    link: LinkSpec | None = None
    audio: str | None = None  # media: a published audio URL
    badge: str | None = None  # string key, e.g. "Checked"
    explanation_copy: str | None = None
    simulated: bool = False
    expects: dict[str, int] = Field(default_factory=dict)  # photo_batch / number_grid: sizes

    def option_ids(self) -> list[str]:
        return [o.id for o in self.options]

    def all_keys(self) -> set[str]:
        keys = {self.copy} | {o.copy for o in self.options}
        for params in [self.params, *[ln.params for ln in self.lines]]:
            keys.update(str(v) for k, v in params.items() if k.endswith("_key"))
        keys.update(ln.copy for ln in self.lines)
        if self.link:
            keys.add(self.link.label_copy)
        if self.badge:
            keys.add(self.badge)
        if self.explanation_copy:
            keys.add(self.explanation_copy)
        return keys


class Answer(BaseModel):
    value: str = ""


@dataclass
class Node:
    """One step of a flow: how to build it, and where an answer leads.

    `advance` returns the next step id, "flow:step" to move to another flow, or None to stay.
    `auto` messages are followed at once (they ask for nothing). `keys` lists every string key the
    node can show, so a test can check all three languages have them.
    """

    build: Callable[[Any], Step]
    advance: Callable[[Any, Answer], str | None]
    keys: tuple[str, ...]
    auto: bool = False
    reentry: str | None = None  # where start() resumes: the home menu re-shows its status first


@dataclass
class Flow:
    id: str
    version: int
    start: str
    nodes: dict[str, Node] = field(default_factory=dict)
