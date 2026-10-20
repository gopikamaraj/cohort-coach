"""Onboarding: language, what she agrees to, and the code that links a second channel.

Each consent is a separate choice, off until she says yes (DPDP). The same text and answers are
used in the bot and in the web app. The choices are stored on the teacher; the web app copies
them to the phone so nothing is sent before she agrees.
"""

from __future__ import annotations

from typing import Any

from services.api.flows.steps import Answer, Flow, Node, Option, Step

CONSENT_VERSION = 1
LANGS = ("en", "hi", "ta")
SCOPES = ("core", "counts", "practice_ai", "share_rehearsal", "feedback")


def _opts(*pairs: tuple[str, str]) -> list[Option]:
    return [Option(id=i, copy=c) for i, c in pairs]


def _consent(ctx: Any) -> dict[str, Any]:
    c = dict(ctx.teacher.consent or {})
    for s in SCOPES:
        c.setdefault(s, False)
    return c


def _set_consent(ctx: Any, scope: str, on: bool) -> None:
    c = _consent(ctx)
    c[scope] = on
    c["v"] = CONSENT_VERSION
    ctx.teacher.consent = c


def _lang_build(ctx: Any) -> Step:
    return Step(
        kind="choice",
        id="lang",
        copy="onb.lang",
        options=_opts(*[(code, f"onb.lang.{code}") for code in LANGS]),
    )


def _lang_advance(ctx: Any, a: Answer) -> str | None:
    ctx.teacher.lang = a.value
    return "welcome"


def _yes_no(step: str, prompt: str, scope: str, nxt: str) -> Node:
    def build(ctx: Any) -> Step:
        return Step(
            kind="choice",
            id=step,
            copy=prompt,
            options=_opts(("yes", "onb.yes"), ("no", "onb.no_thanks")),
        )

    def advance(ctx: Any, a: Answer) -> str | None:
        _set_consent(ctx, scope, a.value == "yes")
        return nxt

    return Node(build, advance, (prompt, "onb.yes", "onb.no_thanks"))


def _core_build(ctx: Any) -> Step:
    return Step(
        kind="choice",
        id="consent_core",
        copy="onb.consent_core",
        options=_opts(("agree", "onb.agree"), ("no", "onb.disagree")),
    )


def _core_advance(ctx: Any, a: Answer) -> str | None:
    if a.value == "agree":
        _set_consent(ctx, "core", True)
        return "consent_counts"
    return "declined"


def _declined_build(ctx: Any) -> Step:
    return Step(
        kind="choice", id="declined", copy="onb.declined", options=_opts(("again", "onb.again"))
    )


def _link_build(ctx: Any) -> Step:
    return Step(kind="message", id="link_offer", copy="onb.link", params={"code": ctx.new_code()})


ONBOARDING = Flow(
    id="onboarding",
    version=1,
    start="lang",
    nodes={
        "lang": Node(
            _lang_build, _lang_advance, ("onb.lang", "onb.lang.en", "onb.lang.hi", "onb.lang.ta")
        ),
        "welcome": Node(
            lambda ctx: Step(kind="message", id="welcome", copy="onb.welcome"),
            lambda ctx, a: "consent_core",
            ("onb.welcome",),
            auto=True,
        ),
        "consent_core": Node(
            _core_build, _core_advance, ("onb.consent_core", "onb.agree", "onb.disagree")
        ),
        "declined": Node(
            _declined_build, lambda ctx, a: "consent_core", ("onb.declined", "onb.again")
        ),
        "consent_counts": _yes_no(
            "consent_counts", "onb.consent_counts", "counts", "consent_practice"
        ),
        "consent_practice": _yes_no(
            "consent_practice", "onb.consent_practice", "practice_ai", "consent_feedback"
        ),
        "consent_feedback": _yes_no(
            "consent_feedback", "onb.consent_feedback", "feedback", "link_offer"
        ),
        "link_offer": Node(_link_build, lambda ctx, a: "t1:menu", ("onb.link",), auto=True),
    },
)
