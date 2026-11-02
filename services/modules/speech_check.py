# ruff: noqa: E501
"""Checks on the text written for the voice, and the English template used when they fail.

`check_speech_output(text, si)` is pure code over the fields the input builder parsed (the sections,
the step count, the digit readings, the module number and count). It returns failure codes, empty when
the text is fine. `template_script(si)` builds the deterministic English fallback from the same
sections: fixed signposts, the approved content unchanged, numbers in words. Other languages have no
template here (no invented translations): the caller keeps the code-built script it has today.
Only reason codes and the input hash are logged, never the text.
"""

from __future__ import annotations

import re

from services.modules.speech_input import SpeechInput, digit_words, number_words

PAUSE = "[pause]"
_QUOTES = '"“”‘’«»„'  # an apostrophe in a word is allowed
_ORDINAL = "_ first second third fourth fifth sixth seventh eighth ninth tenth".split()
_WORDS_LO, _WORDS_HI = 1.0, 1.6


def _words(text: str) -> int:
    return len(text.replace(PAUSE, " ").split())


def _count_word(n: int) -> str:
    return number_words(n)


def opening_phrase(number: int, count: int) -> str:
    """"first of two modules"."""
    return f"{_ORDINAL[number] if number < len(_ORDINAL) else number_words(number)} of {_count_word(count)} modules"


def check_speech_output(text: str, si: SpeechInput) -> list[str]:
    fails: list[str] = []
    bare = text.replace(PAUSE, "")
    if re.search(r"[0-9]", text):
        fails.append("digits")
    if any(c in text for c in _QUOTES):
        fails.append("quotes")
    if re.search(r"[\[\]{}]", bare):
        fails.append("brackets")
    if re.search(r"[*#]", text):
        fails.append("markup")
    sections = si.sections
    if text.count(PAUSE) != 1 + len(sections) or text.rstrip().endswith(PAUSE) is False:
        fails.append("pause_count")  # once after the opening and once after each section, none between steps
    steps = next((s for s in sections if s.tag == "steps"), None)
    if steps is not None and not re.search(rf"\b{number_words(len(steps.steps))}\s+steps?\b", text.lower().replace("-", " ")):
        fails.append("step_count")
    said = re.sub(r"[-\s]+", " ", text.lower())
    for n in re.findall(r"\{digits:(\d+)\}", si.text):
        if digit_words(n) not in said:
            fails.append("digits_reading")
            break
    source_words = sum(_words(s.lines()) for s in sections)
    if not (_WORDS_LO * source_words <= _words(text) <= _WORDS_HI * source_words):
        fails.append("length")
    n, c = si.facts.get("module_number"), si.facts.get("module_count")
    if n is not None and c is not None and opening_phrase(n, c) not in text.split(PAUSE, 1)[0].lower():
        fails.append("opening")
    return fails


def _plain(text: str) -> str:
    """One section's text for the template: {digits:N} digit by digit, other numbers in words, no quotes."""
    text = re.sub(r"\{digits:(\d+)\}", lambda m: digit_words(m[1]), text)
    text = re.sub(r"\d+", lambda m: number_words(int(m[0])) if int(m[0]) < 1000 else m[0], text)
    for q in _QUOTES:
        text = text.replace(q, "")
    return " ".join(text.replace("[", "").replace("]", "").split())


_SIGNPOST = {
    "smaller_step": "A smaller step.",
    "purpose": "What this does.",
    "materials": "What you need.",
    "example": "An example.",
    "check": "How to know it worked.",
}
_STEP_LEAD = ["First,", "Then,", "After that,", "Next,"]


def template_script(si: SpeechInput) -> str | None:
    """The English fallback, or None for another language."""
    if si.facts.get("language") != "en":
        return None
    n, c = si.facts.get("module_number"), si.facts.get("module_count")
    opening = f"This is the {opening_phrase(n, c)}." if n is not None and c is not None else f"{_plain(str(si.facts['title']))}."
    blocks = [opening]
    for s in si.sections:
        if s.tag == "steps":
            k = len(s.steps)
            lines = [f"There {'is' if k == 1 else 'are'} {number_words(k)} step{'s' if k != 1 else ''}."]
            for i, step in enumerate(s.steps):
                lead = "" if k == 1 else ("Last," if i == k - 1 else _STEP_LEAD[min(i, len(_STEP_LEAD) - 1)])
                body = _plain(step)
                body = body[:1].lower() + body[1:] if lead else body
                lines.append(f"{lead} {body}".strip() + ("" if body[-1:] in ".?!" else "."))
            blocks.append(" ".join(lines))
        else:
            body = _plain(s.body)
            blocks.append(f"{_SIGNPOST[s.tag]} {body}" + ("" if body[-1:] in ".?!" else "."))
    return f" {PAUSE} ".join(blocks) + f" {PAUSE}"
