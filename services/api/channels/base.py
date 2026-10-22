"""What every adapter shares: a step turned into plain text and buttons.

An adapter renders; it never computes, decides or calls a model. This module and its siblings
import nothing from `engine/` or `ai/` (a test checks it). The words come from `strings`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.api import strings
from services.api.flows.engine import Turn
from services.api.flows.steps import Step


@dataclass
class Button:
    id: str
    label: str


@dataclass
class Message:
    step_id: str
    kind: str
    text: str
    buttons: list[Button] = field(default_factory=list)
    url: str | None = None
    url_label: str | None = None
    audio: str | None = None
    scene: dict[str, object] | None = None  # a SceneRef: the web app draws it, the bot sends a PNG
    alt: str | None = None  # what the picture shows, in her language


def render_step(step: Step, lang: str) -> Message:
    link = step.link
    return Message(
        step_id=step.id,
        kind=step.kind,
        text=strings.render(step, lang),
        buttons=[Button(o.id, strings.text(lang, o.copy)) for o in step.options],
        url=link.url if link else None,
        url_label=strings.text(lang, link.label_copy) if link else None,
        audio=step.audio,
        scene=step.scene.model_dump() if step.scene else None,
        alt=strings.text(lang, f"sprite.scene.{step.scene.layout}") if step.scene else None,
    )


def render_turn(turn: Turn) -> list[Message]:
    return [render_step(s, turn.lang) for s in turn.steps]


def parse_button(data: str) -> tuple[str, str] | None:
    """Telegram callback data `step_id:option_id`; anything else is ignored."""
    step_id, sep, option_id = data.partition(":")
    return (step_id, option_id) if sep and step_id and option_id else None
