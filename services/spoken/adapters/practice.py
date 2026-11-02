"""Practice Class adapter: one deterministic call before a line is voiced. No model, no extra wait.

Child lines are either template lines (services/practice/templates.py) or the runtime model's
line (call 1), which arrives as a full response and may carry numbers. Both go through the same
normaliser, sentence by sentence, right before synthesis. The simulated child's number, the one the
engine chose, is read as an ordinary number: it is not a place-value example unless a template or
the prompt marks it {pv:N}. The on-screen line is not changed.
"""

from __future__ import annotations

import logging

from services.spoken.normalizer import normalize
from services.spoken.render import to_plain
from services.spoken.validators import validate

log = logging.getLogger(__name__)


def prepare_utterance(text: str, language: str, speaker: str = "simulated_child") -> str:
    """Spoken-ready text for one line. Only counts are logged, never the line."""
    spoken = to_plain(normalize(text, language))
    issues = validate(spoken, language, speaker)
    if issues:
        log.info(
            "spoken: %d issue(s) in a %s line: %s", len(issues), speaker, [i.code for i in issues]
        )
    return spoken
