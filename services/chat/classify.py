"""The class of a question: safety words first, in code; a model only for what code cannot decide.

Order, and why:

1. **Safety and welfare words** (content/safety/welfare_terms.yaml, three languages) are checked in
   code before anything else. A hit means the question goes straight to the coach with a flag and
   no model reads it. This holds even if the teacher did not tick AI help.
2. A replaced child name, roll number or relative means the question is about a particular child:
   child-specific, without a model call.
3. Discipline and personal words route the question to the mentor (a draft may be made for her
   only, and is never sent on its own).
4. Anything else goes to call 12, only if the teacher ticked AI help. Low confidence or any failure
   is "unclear".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai.calls.c12_chat_classify import classify_with_model
from ai.client import CallContext, CallResult
from ai.validators._data import load_yaml, token_matches, tokens
from ai.validators.mask import Masked

CLASSES = (
    "content_question",
    "child_specific",
    "safety_or_welfare",
    "discipline_or_personal",
    "off_topic",
    "unclear",
)
# Classes for which a draft may be made, for the mentor to read. Only content_question may ever
# be sent on its own (services/chat/scheduler.py).
DRAFTABLE = ("content_question", "child_specific", "discipline_or_personal")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class Classification:
    label: str | None  # None: nobody classified it (the teacher did not ask for AI help)
    source: str  # rule | model | fallback | none
    confidence: float | None = None
    run: CallResult | None = None


def _hits(kind: str, text: str) -> bool:
    data = load_yaml("safety/welfare_terms.yaml")[kind]
    toks = tokens(text)
    flat = _SPACES.sub(" ", text.casefold())
    for lang, words in data.items():
        suffix = 3 if lang == "ta" else 0
        for word in words:
            w = str(word).casefold()
            if " " in w:
                if w in flat:
                    return True
            elif any(token_matches(t, w, suffix=suffix) for t in toks):
                return True
    return False


def rule_label(masked: Masked) -> str | None:
    """The label code can decide on its own, or None if only a model could."""
    if _hits("safety", masked.text):
        return "safety_or_welfare"
    if masked.child_mentioned:
        return "child_specific"
    if _hits("discipline", masked.text):
        return "discipline_or_personal"
    return None


def classify(
    masked: Masked,
    language: str,
    *,
    use_model: bool,
    context: CallContext | None = None,
) -> Classification:
    ruled = rule_label(masked)
    if ruled is not None:
        return Classification(ruled, "rule")
    if not use_model:
        return Classification(None, "none")
    result = classify_with_model(masked.text, language, context=context)
    source = "fallback" if result.fell_back else "model"
    return Classification(result.label, source, result.confidence, result.run)
