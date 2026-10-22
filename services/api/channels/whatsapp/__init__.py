"""WhatsApp adapter: a stub. Messages become numbered text; a reply "2" picks option 2.

The WhatsApp Cloud API sender is roadmap. What is here is the contract a real sender plugs into.
"""

from __future__ import annotations

from services.api.channels.base import Message


def to_text(m: Message) -> str:
    lines = [m.text]
    if m.alt:  # the picture goes as a PNG once the Cloud API sender exists
        lines.append(f"[{m.alt}]")
    if m.url:
        lines.append(f"{m.url_label}: {m.url}")
    lines += [f"{i}. {b.label}" for i, b in enumerate(m.buttons, 1)]
    return "\n".join(lines)


def parse_reply(text: str, shown: Message) -> str | None:
    """The option id a typed number picks on the message she was shown, or None."""
    t = text.strip()
    if t.isdigit() and 1 <= int(t) <= len(shown.buttons):
        return shown.buttons[int(t) - 1].id
    return None
