"""Turn text written for the screen into text that can be spoken. Deterministic and idempotent:
running it on its own output changes nothing. It never calls a model.

What it does, in order:
  1. pause tokens are set aside, {pv:N} place-value numbers are said digit by digit
  2. markdown, HTML, bullets and links go; bullets and lines become sentences
  3. screen-only text goes: "Source: ...", "Draft", and "Label:" prefixes (a known label is
     spoken as a phrase, "Materials:" becomes "You will need")
  4. "N of M children" becomes a spoken ratio
  5. math symbols between numbers become words (plus, minus, times, equals ...)
  6. every remaining number becomes words (up to 9999; longer ones digit by digit)
  7. leftover symbols go, punctuation is tidied, and every line ends like a sentence
"""

from __future__ import annotations

import re
import unicodedata

from services.spoken.lang import pack_for
from services.spoken.lang.base import LanguagePack
from services.spoken.schema import PAUSE_LONG, PAUSE_SHORT, PV_RE

_SHORT, _LONG = "", ""  # stand-ins for the pause tokens while the text is worked on
_END = ".?!।"
_ASCII_DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯", "0123456789" * 2)

_SOURCE_LINE = re.compile(r"^\s*(source|sources|स्रोत|மூலம்)\s*[:：—-]", re.I)
_SOURCE_INLINE = re.compile(r"\s*[·•|]\s*(source|स्रोत|மூலம்)\s*[:：—-][^\n]*", re.I)
_DRAFT = re.compile(r"\s*(?:[·•|]\s*|\(|\[)\s*(?:draft|मसौदा|வரைவு)\s*[)\]]?", re.I)
_DRAFT_LINE = re.compile(r"^\s*(draft|मसौदा|வரைவு)\s*[.:]?\s*$", re.I)
_LABEL = re.compile(r"^\s*([^\W\d_][^\W\d_ ]*(?: [^\W\d_][^\W\d_ ]*){0,2})\s*[:：]\s*(.*)$")
_LABEL_ALONE = re.compile(r"^\s*([^\W\d_][^\W\d_ ]*(?: [^\W\d_][^\W\d_ ]*){0,2})\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•·▪◦]|\d{1,2}[.)])\s+")
_RATIO_EN = re.compile(r"\b(\d+)\s+of\s+(\d+)(\s+(?:children|child|pupils|students))?", re.I)
_ORDINAL = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b", re.I)
_MATH = re.compile(r"(?<=\d)\s*([+×÷=<>−–*]|(?<=\s)-(?=\s)|\bx\b|(?<=\s)/(?=\s)|/)\s*(?=\d)")
_DECIMAL = re.compile(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])")
_NUMBER = re.compile(r"\d+")

# the labels the screen puts in front of text; each is spoken as a phrase from the language pack
_SCREEN_LABELS = {
    "materials", "steps", "worked example", "example from your class", "roll numbers",
    "note", "सामग्री", "कदम", "उदाहरण", "रोल नंबर", "பொருட்கள்", "படிகள்", "எடுத்துக்காட்டு",
    "பதிவு எண்கள்",
}  # fmt: skip
_MATH_WORD = {
    "+": "+",
    "×": "x",
    "*": "x",
    "x": "x",
    "÷": "/",
    "/": "/",
    "=": "=",
    "<": "<",
    ">": ">",
    "−": "-",
    "–": "-",
    "-": "-",
}


def _say_number(pack: LanguagePack, digits: str) -> str:
    if len(digits) > 1 and digits.startswith("0") or len(digits) > 4:
        return pack.digits_to_words(digits)
    return pack.number_to_words(int(digits))


def _pv(pack: LanguagePack, digits: str) -> str:
    """A place-value number, said one digit at a time with a breath between them."""
    return ", ".join(pack.digit_words[int(d)] for d in digits)


def _sentence_end(line: str) -> str:
    line = line.rstrip(" ,;:-")
    if not line:
        return line
    if line[-1] in _END + _SHORT + _LONG:
        return line
    return line + ("।" if "ऀ" <= line[-1] <= "ॿ" else ".")


def _line(line: str, pack: LanguagePack) -> str:
    if _SOURCE_LINE.match(line) or _DRAFT_LINE.match(line):
        return ""
    line = _SOURCE_INLINE.sub("", line)
    line = _DRAFT.sub("", line)
    bullet = bool(_BULLET.match(line))
    line = _BULLET.sub("", line)
    m = _LABEL.match(line)
    if m and m.group(1).lower() in _SCREEN_LABELS:
        spoken = pack.label_phrases.get(m.group(1).lower(), "")
        rest = m.group(2).strip()
        line = f"{spoken} {rest}".strip() if rest else spoken
    elif m and not re.search(r"\d", m.group(1)):
        # a label that is not a screen label ("Ask: ..."): keep the words, the colon becomes a comma
        line = f"{m.group(1)}, {m.group(2)}".strip(" ,")
    elif (a := _LABEL_ALONE.match(line)) and a.group(1).lower() in pack.label_phrases:
        line = pack.label_phrases[a.group(1).lower()]
    if bullet:
        line = line.strip()
    return line


def normalize(text: str, language: str = "en") -> str:
    """Spoken-ready text for `language`. See the module docstring."""
    pack = pack_for(language)
    t = unicodedata.normalize("NFC", text).translate(_ASCII_DIGITS)
    t = PV_RE.sub(lambda m: _pv(pack, m.group(1)), t)
    t = t.replace(PAUSE_LONG, _LONG).replace(PAUSE_SHORT, _SHORT)
    # markup
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"(\*\*|__|`)", "", t)
    t = re.sub(r"^\s*#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)", "", t)
    lines = [_line(ln, pack) for ln in t.split("\n")]
    t = "\n".join(lines)
    # data phrases
    t = (
        _RATIO_EN.sub(lambda m: pack.ratio_phrase(int(m.group(1)), int(m.group(2))), t)
        if pack.code == "en"
        else t
    )
    # math between numbers
    t = _MATH.sub(lambda m: f" {pack.math_words[_MATH_WORD.get(m.group(1), m.group(1))]} ", t)
    t = re.sub(r"(\d)\s*%", lambda m: f"{m.group(1)} {pack.math_words['%']}", t)
    t = _ORDINAL.sub(lambda m: pack.ordinal(int(m.group(1))), t) if pack.code == "en" else t
    t = re.sub(r"(?<=\d)-(?=\d)", " ", t)  # 5-10: two numbers side by side
    t = _DECIMAL.sub(
        lambda m: (
            f"{_say_number(pack, m.group(1))} {pack.math_words['point']} "
            f"{pack.digits_to_words(m.group(2))}"
        ),
        t,
    )
    t = _NUMBER.sub(lambda m: _say_number(pack, m.group(0)), t)
    # punctuation and leftovers
    t = t.replace("&", f" {pack.phrases.get('and', 'and')} ")
    t = re.sub(
        r"[\"“]([^\"”\n]+)[\"”]", lambda m: f", {m.group(1).strip()}, ", t
    )  # a quoted line is set off by commas
    t = re.sub(r"[\"“”‘’«»]", "", t)
    t = re.sub(r"\s*[(\[]\s*", ", ", t)
    t = re.sub(r"\s*[)\]]\s*", ", ", t)
    t = re.sub(r"\s+[—–-]+\s+", ", ", t)
    t = re.sub(r"[;:：]", ",", t)
    t = t.replace("…", ".")
    t = re.sub(r"[*_#`~^|\\<>{}=+×÷−]", " ", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+([,.?!।])", r"\1", t)
    t = re.sub(r"([.?!।]),", r"\1", t)
    t = re.sub(r",\s*([.?!।])", r"\1", t)
    t = re.sub(r"\.{2,}", ".", t)
    out: list[str] = []
    for ln in t.split("\n"):
        ln = ln.strip(" ,")
        out.append(_sentence_end(ln) if ln else "")
    t = "\n".join(out)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    # restore the pauses: one after a sentence, never two in a row (the long one wins)
    t = re.sub(
        f"[{_SHORT}{_LONG}](?:\\s*[{_SHORT}{_LONG}])+",
        lambda m: _LONG if _LONG in m.group(0) else _SHORT,
        t,
    )
    t = re.sub(f"[ \\t]*([{_SHORT}{_LONG}])[ \\t]*", r" \1 ", t)
    t = t.replace(_LONG, PAUSE_LONG).replace(_SHORT, PAUSE_SHORT)
    t = re.sub(r"[ \t]*\n[ \t]*", "\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()
