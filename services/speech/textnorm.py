"""Text normalisation for comparing what was meant with what a speech service heard: lower case, no
punctuation, single spaces, Devanagari and Tamil digits as ASCII, and number words turned into
digits (English 0 to 999 999; Hindi and Tamil 0 to 100 plus hundreds and thousands). Then the
character and word error rates, by edit distance.

The Hindi and Tamil number words are a first draft for the round-trip check and the speech-to-text
eval only; they never reach a teacher. TODO-HUMAN(Seema: Hindi, Gopi: Tamil): check the word lists.
"""

from __future__ import annotations

import re
import unicodedata

_DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯", "0123456789" * 2)

_EN_UNITS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
_EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
EN = {w: i for i, w in enumerate(_EN_UNITS)} | {
    w: 10 * i for i, w in enumerate(_EN_TENS) if w != "_"
}
EN_SCALE = {"hundred": 100, "thousand": 1000}

# Hindi 0-100 (each number has its own word).
_HI_1_100 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
    "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस "
    "चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस "
    "छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन "
    "उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर "
    "तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी "
    "पचासी छियासी सत्तासी अठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे "
    "सत्तानवे अट्ठानवे निन्यानवे सौ"
).split()
HI = {w: i for i, w in enumerate(_HI_1_100)} | {"पांच": 5, "छः": 6, "छे": 6}
HI_SCALE = {"सौ": 100, "हज़ार": 1000, "हजार": 1000}

# Tamil: units, tens and the combining forms used before a unit (e.g. இருபத்து மூன்று = 23).
TA = {
    "பூஜ்ஜியம்": 0,
    "ஒன்று": 1,
    "இரண்டு": 2,
    "மூன்று": 3,
    "நான்கு": 4,
    "ஐந்து": 5,
    "ஆறு": 6,
    "ஏழு": 7,
    "எட்டு": 8,
    "ஒன்பது": 9,
    "பத்து": 10,
    "பதினொன்று": 11,
    "பன்னிரண்டு": 12,
    "பதின்மூன்று": 13,
    "பதினான்கு": 14,
    "பதினைந்து": 15,
    "பதினாறு": 16,
    "பதினேழு": 17,
    "பதினெட்டு": 18,
    "பத்தொன்பது": 19,
    "இருபது": 20,
    "முப்பது": 30,
    "நாற்பது": 40,
    "ஐம்பது": 50,
    "அறுபது": 60,
    "எழுபது": 70,
    "எண்பது": 80,
    "தொண்ணூறு": 90,
    "நூறு": 100,
    "இருபத்து": 20,
    "முப்பத்து": 30,
    "நாற்பத்து": 40,
    "ஐம்பத்து": 50,
    "அறுபத்து": 60,
    "எழுபத்து": 70,
    "எண்பத்து": 80,
    "தொண்ணூற்று": 90,
}
TA_SCALE = {"நூறு": 100, "ஆயிரம்": 1000}
# Hundreds as single words in Tamil (இருநூறு = 200 ...), and the combining forms (இருநூற்று ...).
TA_HUNDREDS = {
    "நூற்று": 100,
    "இருநூறு": 200,
    "இருநூற்று": 200,
    "முன்னூறு": 300,
    "முன்னூற்று": 300,
    "நானூறு": 400,
    "நானூற்று": 400,
    "ஐந்நூறு": 500,
    "ஐந்நூற்று": 500,
    "அறுநூறு": 600,
    "அறுநூற்று": 600,
    "எழுநூறு": 700,
    "எழுநூற்று": 700,
    "எண்ணூறு": 800,
    "எண்ணூற்று": 800,
    "தொள்ளாயிரம்": 900,
    "தொள்ளாயிரத்து": 900,
}


def _words_to_number(words: list[str], lang: str) -> tuple[int, int] | None:
    """(value, how many words used) for a number starting at words[0], or None."""
    small = EN if lang == "en" else HI if lang == "hi" else TA
    scale = EN_SCALE if lang == "en" else HI_SCALE if lang == "hi" else TA_SCALE
    total, current, used = 0, 0, 0
    for k, w in enumerate(words):
        if lang == "ta" and w in TA_HUNDREDS:
            current += TA_HUNDREDS[w]
        elif w in scale and (lang != "hi" or w != "सौ" or current):
            mult = scale[w]
            if mult == 1000:
                total += max(current, 1) * 1000
                current = 0
            else:
                current = max(current, 1) * mult
        elif w in small:
            current += small[w]
        elif lang == "en" and w == "and" and used and k + 1 < len(words) and words[k + 1] in small:
            pass  # "one hundred and five"; a plain "and" between numbers ends the number
        else:
            break
        used += 1
    if used == 0:
        return None
    return total + current, used


def parse_number_words(text: str) -> int | None:
    """The whole text as one number (English, Hindi or Tamil words, 0 to 9999), or None if any word
    is not part of a number. Hyphens, dashes and a plain "and" are ignored."""
    t = unicodedata.normalize("NFC", text).lower()
    t = re.sub(r"[-\u2010-\u2015,.]", " ", t)
    words = [w for w in t.split() if w]
    if not words:
        return None
    for lang in ("en", "hi", "ta"):
        got = _words_to_number(words, lang)
        if got is not None and got[1] == len(words) and 0 <= got[0] <= 9999:
            return got[0]
    return None


def numbers_to_digits(text: str, lang: str) -> str:
    words = text.split()
    out: list[str] = []
    i = 0
    while i < len(words):
        got = _words_to_number(words[i:], lang)
        if got is None:
            out.append(words[i])
            i += 1
        else:
            out.append(str(got[0]))
            i += got[1]
    return " ".join(out)


def normalise(text: str, lang: str, numbers: bool = True) -> str:
    """For comparison only: NFC, ASCII digits, lower case, no punctuation, number words as
    digits."""
    t = unicodedata.normalize("NFC", text).translate(_DIGITS).lower()
    t = t.replace("-", " ")
    t = "".join(
        ch if ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("M") else " "
        for ch in t
    )
    t = re.sub(r"\s+", " ", t).strip()
    return numbers_to_digits(t, lang) if numbers else t


def _distance(a: list[str] | str, b: list[str] | str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def cer(reference: str, heard: str, lang: str) -> float:
    """Character error rate after normalising both (spaces ignored). 0 is a perfect match."""
    ref = normalise(reference, lang).replace(" ", "")
    hyp = normalise(heard, lang).replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    return _distance(ref, hyp) / len(ref)


def wer(reference: str, heard: str, lang: str) -> float:
    ref = normalise(reference, lang).split()
    hyp = normalise(heard, lang).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _distance(ref, hyp) / len(ref)


def numbers_in(text: str, lang: str) -> list[int]:
    return [int(w) for w in normalise(text, lang).split() if w.isdigit()]
