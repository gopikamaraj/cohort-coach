"""T1 Home: what she has done this term (in counts) and the next actions.

Numbers are counts and come from class-level counts via `facts`; the flow never computes a statistic
itself. A judge's numbers come from the simulated block and every step built from them says so. The
check by photo is built in P08; until then the check step says where to type the answers.
"""

from __future__ import annotations

import os
from typing import Any

from services.api.flows.links import sign
from services.api.flows.onboarding import SCOPES  # noqa: F401  (re-exported for adapters' tests)
from services.api.flows.steps import Answer, Flow, Line, LinkSpec, Node, Option, Step

TRACKED = ("PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC", "PV-REVERSE")


def base_url() -> str:
    return (
        os.environ.get("PWA_PUBLIC_URL") or os.environ.get("PWA_ORIGIN") or "http://localhost:5173"
    ).rstrip("/")


def _status_build(ctx: Any) -> Step:
    s = ctx.summary
    if s is None:
        return Step(kind="message", id="status", copy="t1.status_none")
    return Step(
        kind="message",
        id="status",
        copy="t1.status",
        params={"n": s.checked},
        simulated=s.simulated,
    )


def _menu_build(ctx: Any) -> Step:
    opts = [
        ("practice", "t1.o.practice"),
        ("cards", "t1.o.cards"),
        ("check", "t1.o.check"),
        ("delete", "t1.o.delete"),
    ]
    return Step(
        kind="choice", id="menu", copy="t1.menu", options=[Option(id=i, copy=c) for i, c in opts]
    )


def _menu_advance(ctx: Any, a: Answer) -> str | None:
    return {
        "practice": "practice",
        "cards": "cards",
        "check": "check_info",
        "delete": "confirm_delete",
    }[a.value]


def _cards_build(ctx: Any) -> Step:
    s = ctx.summary
    if s is None:
        return Step(kind="message", id="cards", copy="t1.cards_none")
    shown = [(code, n) for code in TRACKED if (n := s.counts.get(code, 0)) > 0]
    if not shown:
        return Step(kind="message", id="cards", copy="t1.cards_clear", simulated=s.simulated)
    # one line per error, counts only: "11 of 28 children take the smaller digit from the larger."
    lines = [
        Line(copy="cards.line", params={"n": n, "total": s.checked, "desc_key": f"err.desc.{code}"})
        for code, n in shown
    ]
    return Step(
        kind="message", id="cards", copy="t1.cards_head", lines=lines, simulated=s.simulated
    )


def _practice_build(ctx: Any) -> Step:
    s = ctx.summary
    scenario = (
        s.track
        if s and s.track in ("PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC")
        else "SUB-SFL"
    )
    token = sign({"lang": ctx.teacher.lang, "scenario": scenario})
    return Step(
        kind="link",
        id="practice",
        copy="t1.practice",
        link=LinkSpec(
            kind="practice", label_copy="t1.practice_open", url=f"{base_url()}/#/practice?t={token}"
        ),
        options=[Option(id="back", copy="t1.back")],
    )


def _confirm_build(ctx: Any) -> Step:
    return Step(
        kind="choice",
        id="confirm_delete",
        copy="t1.confirm_delete",
        options=[Option(id="yes", copy="t1.yes_delete"), Option(id="no", copy="t1.keep")],
    )


def goodbye() -> Step:
    return Step(kind="message", id="deleted", copy="t1.deleted")


T1 = Flow(
    id="t1",
    version=1,
    start="status",
    nodes={
        "status": Node(
            _status_build, lambda ctx, a: "menu", ("t1.status", "t1.status_none"), auto=True
        ),
        "menu": Node(
            _menu_build,
            _menu_advance,
            ("t1.menu", "t1.o.practice", "t1.o.cards", "t1.o.check", "t1.o.delete"),
            reentry="status",
        ),
        "cards": Node(
            _cards_build,
            lambda ctx, a: "menu",
            (
                "t1.cards_none",
                "t1.cards_clear",
                "t1.cards_head",
                "cards.line",
                *[f"err.desc.{c}" for c in TRACKED],
            ),
            auto=True,
        ),
        "check_info": Node(
            lambda ctx: Step(kind="message", id="check_info", copy="t1.check_info"),
            lambda ctx, a: "menu",
            ("t1.check_info",),
            auto=True,
        ),
        "practice": Node(
            _practice_build, lambda ctx, a: "menu", ("t1.practice", "t1.practice_open", "t1.back")
        ),
        "confirm_delete": Node(
            _confirm_build,
            lambda ctx, a: "end:deleted" if a.value == "yes" else "menu",
            ("t1.confirm_delete", "t1.yes_delete", "t1.keep"),
        ),
    },
)
