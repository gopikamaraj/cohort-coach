"""The shared spoken layer: spoken text is its own output, separate from the screen text.

normalizer -> validators -> pause markers -> TTS-target renderer      (shared core)
adapters/intervention.py   structured content -> builders -> core
adapters/practice.py       a line, sentence by sentence -> core, no model on the hot path
"""

from services.spoken.normalizer import normalize
from services.spoken.render import Piece, pieces, to_plain, to_ssml
from services.spoken.schema import PAUSE_LONG, PAUSE_SHORT, SpokenScript, Utterance
from services.spoken.validators import Issue, validate

__all__ = [
    "PAUSE_LONG",
    "PAUSE_SHORT",
    "Issue",
    "Piece",
    "SpokenScript",
    "Utterance",
    "normalize",
    "pieces",
    "to_plain",
    "to_ssml",
    "validate",
]
