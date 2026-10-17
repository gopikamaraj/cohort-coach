"""Template child lines: the deterministic fallback for call 1, and the plain-English meaning of
each step that is handed to Claude. Pure: the numbers come from the plan, the words from
content/templates/child_lines.<lang>.yaml."""

from __future__ import annotations

from engine.simulator import Step, TurnPlan
from services.practice.content import load_templates


def step_text(step: Step, lang: str) -> str:
    t = load_templates(lang)
    pattern = t.steps[step.op]
    parts = t.and_.join(str(n) for n in step.numbers[:-1])
    return pattern.format(*step.numbers, parts=parts, r=step.numbers[-1])


def steps_text(steps: tuple[Step, ...], lang: str) -> str:
    t = load_templates(lang)
    return t.join.join(step_text(s, lang) for s in steps)


def render_line(plan: TurnPlan, lang: str) -> str:
    """The template line for a plan; empty when nobody speaks."""
    if plan.speaker is None:
        return ""
    t = load_templates(lang)
    intent = plan.intent
    if intent in {"explain", "work_aloud", "doubt"} and plan.steps:
        return t.intents[intent].format(steps=steps_text(plan.steps, lang))
    if intent in {"explain", "work_aloud", "doubt"} and plan.answer is not None:
        return t.intents["answer"].format(answer=plan.answer)
    if intent == "answer" and plan.answer is not None:
        return t.intents["answer"].format(answer=plan.answer)
    if intent in {"agree", "thanks", "quiet", "confused"}:
        return t.intents[intent]
    return t.intents["confused"]
