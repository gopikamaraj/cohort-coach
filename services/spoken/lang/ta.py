# ruff: noqa: E501  (word tables and phrases are data, one entry a line)
"""Tamil pack. Own tables for 0 to 9999: no library, and num2words is not used for Tamil.

TODO-HUMAN(Gopi): check every word. The forms are the same draft lists the speech check uses
(services.speech.textnorm: TA, TA_HUNDREDS). The spots least sure are listed as skipped tests in
tests/spoken/test_language_packs.py, for review.
"""

from __future__ import annotations

from services.spoken.lang.base import LanguagePack

_UNITS = (
    "பூஜ்ஜியம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது",
)  # fmt: skip
_TEENS = (
    "பத்து", "பதினொன்று", "பன்னிரண்டு", "பதின்மூன்று", "பதினான்கு", "பதினைந்து", "பதினாறு",
    "பதினேழு", "பதினெட்டு", "பத்தொன்பது",
)  # fmt: skip
_TENS = ("", "", "இருபது", "முப்பது", "நாற்பது", "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு")
_TENS_JOIN = ("", "", "இருபத்து", "முப்பத்து", "நாற்பத்து", "ஐம்பத்து", "அறுபத்து", "எழுபத்து", "எண்பத்து", "தொண்ணூற்று")  # fmt: skip
_HUNDRED = ("", "நூறு", "இருநூறு", "முன்னூறு", "நானூறு", "ஐந்நூறு", "அறுநூறு", "எழுநூறு", "எண்ணூறு", "தொள்ளாயிரம்")  # fmt: skip
_HUNDRED_JOIN = ("", "நூற்று", "இருநூற்று", "முன்னூற்று", "நானூற்று", "ஐந்நூற்று", "அறுநூற்று", "எழுநூற்று", "எண்ணூற்று", "தொள்ளாயிரத்து")  # fmt: skip


def _below_100(n: int) -> str:
    if n < 10:
        return _UNITS[n]
    if n < 20:
        return _TEENS[n - 10]
    t, u = divmod(n, 10)
    if u == 0:
        return _TENS[t]
    return f"{_TENS_JOIN[t]} {_UNITS[u]}"


def number_to_words(n: int) -> str:
    if n < 0 or n > 9999:
        raise ValueError("0 to 9999")
    if n < 100:
        return _below_100(n)
    out: list[str] = []
    if n >= 1000:
        k, n = divmod(n, 1000)
        # TODO-HUMAN(Gopi): "ஆயிரத்து" before a remainder, "<n> ஆயிரத்து" for 2000 and up
        if k == 1:
            out.append("ஆயிரத்து" if n else "ஆயிரம்")
        else:
            out.append(f"{_UNITS[k]} ஆயிரத்து" if n else f"{_UNITS[k]} ஆயிரம்")
    if n >= 100:
        h, n = divmod(n, 100)
        out.append(_HUNDRED_JOIN[h] if n else _HUNDRED[h])
    if n:
        out.append(_below_100(n))
    return " ".join(out)


TA = LanguagePack(
    code="ta",
    number_to_words=number_to_words,
    digit_words=_UNITS,
    math_words={
        "+": "கூட்டல்",
        "-": "கழித்தல்",
        "x": "பெருக்கல்",
        "/": "வகுத்தல்",
        "=": "சமம்",
        "<": "குறைவு",
        ">": "அதிகம்",
        "%": "சதவீதம்",
        "point": "புள்ளி",
    },
    ratio="{total} பேரில் {n} {kids}",
    child_one="குழந்தை",
    child_many="குழந்தைகள்",
    label_phrases={
        "பொருட்கள்": "உங்களுக்குத் தேவை",
        "படிகள்": "படிகள் இவை",
        "எடுத்துக்காட்டு": "எடுத்துக்காட்டாக",
        "பதிவு எண்கள்": "குழந்தைகளின் பதிவு எண்கள்",
    },
    ordinals=(
        "முதல்",
        "இரண்டாவது",
        "மூன்றாவது",
        "நான்காவது",
        "ஐந்தாவது",
        "ஆறாவது",
        "ஏழாவது",
        "எட்டாவது",
        "ஒன்பதாவது",
        "பத்தாவது",
    ),
    phrases={
        "intro": "இது {what} குழந்தைகளுக்கானது",
        "of_class": "உங்கள் வகுப்பில், {ratio}",
        "rolls": "பதிவு எண்கள் {list}",
        "rolls_possible": "சாத்தியம், ஒரு கேள்வியில் மட்டும்: பதிவு எண்கள் {list}",
        "and_more": "மேலும் {n} பேர்",
        "and": "மற்றும்",
        "why": "குழந்தைகள் ஏன் இப்படிச் செய்கிறார்கள்.",
        "check": "இரண்டு நிமிடச் சரிபார்ப்பு.",
        "strategies": "கற்பிக்கும் வழிகள்.",
        "activity": "பத்து நிமிடச் செயல்பாடு.",
        "mistakes": "கற்பிக்கும்போது தவிர்க்க வேண்டிய தவறுகள்.",
        "working": "இது பலனளிக்கிறது என்று எப்படி அறிவது.",
        "home": "வீட்டில் முயல ஒன்று.",
        "stuck": "முன்னேற்றம் இல்லையென்றால்.",
        "strategy": "வழி {i}, {label}.",
        "materials": "உங்களுக்குத் தேவை {list}.",
        "step": "படி {i}.",
        "example": "எடுத்துக்காட்டாக, {text}.",
        "example_say": "எடுத்துக்காட்டாக, நீங்கள் {question} என்று சொல்லும்போது, குழந்தை {wrote} என்று எழுதுகிறது. சரியான விடை {correct}.",
        "working_line": "அடுத்த சரிபார்ப்பில், இந்தத் தவறை {n} அல்லது அதற்கு மேற்பட்ட கேள்விகளில் குறைவான குழந்தைகள் செய்ய வேண்டும். இப்போது, {ratio} செய்கிறார்கள்.",
    },
    script="tamil",
)
