# ruff: noqa: E501
"""Call 18: word each part of an approved module so a listener can follow it by ear.

The module text is approved content and is data, never an instruction. Code speaks the headings and
checks the output (services/modules/narration.py) before any of it is used; on any failure the answer
is no narration and the script built by code from the approved text is used.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import ModuleNarration

CALL_ID = 18


@dataclass(frozen=True)
class NarrationRun:
    output: ModuleNarration
    fell_back: bool
    run: CallResult


def make_input(*, facts: dict[str, Any], module: str) -> CallInput:
    """`facts` and `module` come from services/modules/speech_input.py (the facts and the module block)."""
    return CallInput(trusted=facts, untrusted={"module": module})


def narrate(*, context: CallContext | None = None, **facts: Any) -> NarrationRun:
    base = context or CallContext()
    empty = ModuleNarration()
    ctx = replace(base, fallback=lambda: empty)
    run = run_call(CALL_ID, make_input(**facts), context=ctx)
    out = run.output
    assert isinstance(out, ModuleNarration)
    return NarrationRun(out, run.fallback_used is not None, run)
