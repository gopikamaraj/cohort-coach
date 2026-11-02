"""From spoken text to what a speech engine takes.

Neither Bodhan nor Sarvam takes SSML today (both take plain text, a voice and a style), so the
plain target cuts the text at its pauses into pieces: the speech layer voices each piece and the
silence between them is added to the audio (services.speech.lessons.stitch). `to_ssml` is for an
engine that does take SSML; nothing calls it yet. Pause lengths come from content/spoken.yaml.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from xml.sax.saxutils import escape

from services.spoken.schema import PAUSE_LONG, PAUSE_RE, PAUSE_SHORT
from services.spoken.validators import config

_SPLIT = re.compile(r"(\[pause:long\]|\[pause\])")


@dataclass(frozen=True)
class Piece:
    text: str
    pause_after_ms: int  # silence to add after this piece (0 at the very end)


def pause_ms(token: str) -> int:
    p = config()["pauses_ms"]
    return int(p["long"] if token == PAUSE_LONG else p["short"])


def pieces(text: str) -> list[Piece]:
    out: list[Piece] = []
    cur = ""
    for part in _SPLIT.split(text):
        if part in (PAUSE_SHORT, PAUSE_LONG):
            if cur.strip():
                out.append(Piece(cur.strip(), pause_ms(part)))
                cur = ""
            elif out:  # a pause after a pause: the longer one
                last = out[-1]
                out[-1] = Piece(last.text, max(last.pause_after_ms, pause_ms(part)))
        else:
            cur += part
    if cur.strip():
        out.append(Piece(cur.strip(), 0))
    return out


def to_plain(text: str) -> str:
    """The text with no pause tokens: what a provider that cannot pause reads in one go."""
    return re.sub(r"[ \t]{2,}", " ", PAUSE_RE.sub(" ", text)).strip()


def to_ssml(text: str) -> str:
    body = ""
    for p in pieces(text):
        body += escape(p.text)
        if p.pause_after_ms:
            body += f'<break time="{p.pause_after_ms}ms"/>'
    return f"<speak>{body}</speak>"
