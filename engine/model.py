"""Core types of the deterministic engine. Pure data: no I/O, no randomness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class ErrorCode(StrEnum):
    PV_HEARD = "PV-HEARD"
    PV_REVERSE = "PV-REVERSE"
    ADD_NOCARRY = "ADD-NOCARRY"
    SUB_SFL = "SUB-SFL"
    SUB_NODEC = "SUB-NODEC"


class ItemType(StrEnum):
    DICTATION = "dictation"
    ADD_CARRY = "add_carry"
    SUB_ANCHOR = "sub_anchor"
    SUB_BORROW = "sub_borrow"


# Untracked pattern: the whole ones total written in (38 + 47 -> 715). Scored "other", tallied.
ADD_WHOLE_ONES = "ADD-WHOLE-ONES"


class Mark(StrEnum):
    CORRECT = "correct"
    ERROR = "error"
    OTHER = "other"
    BLANK = "blank"
    UNREADABLE = "unreadable"


# What the reader (teacher, call 8 or the normaliser) hands to the engine for one answer box.
Reading = int | Literal["blank", "unreadable"]


@dataclass(frozen=True)
class Item:
    """One check item. For a dictation item `a` is the number said and `b` is unused."""

    n: int
    type: ItemType
    a: int
    b: int = 0


@dataclass(frozen=True)
class Form:
    label: str
    items: tuple[Item, ...]


@dataclass(frozen=True)
class AnswerMark:
    kind: Mark
    codes: frozenset[ErrorCode] = frozenset()
    untracked: str | None = None


@dataclass(frozen=True)
class ChildDiagnosis:
    marks: tuple[AnswerMark, ...]
    shows: frozenset[ErrorCode]
    anchor_wrong: bool
    other_count: int
    blank_count: int
    unreadable_count: int
    untracked: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassProfile:
    children_checked: int
    counts: Mapping[ErrorCode, int]
    prevalence: Mapping[ErrorCode, float]
    eligible: tuple[ErrorCode, ...]
    track: ErrorCode | None
    anchor_wrong_count: int
    untracked: Mapping[str, int]
