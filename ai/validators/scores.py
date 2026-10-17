"""Feedback must carry no score, grade or rating of the teacher."""

from __future__ import annotations

import re

from ai.validators import Violation
from ai.validators._data import ascii_digits

_PATTERNS = (
    re.compile(r"\d+\s*/\s*\d+"),  # 8/10
    re.compile(r"\d+\s*%"),  # 80%
    re.compile(r"out of \d+", re.IGNORECASE),
    re.compile(r"\b(score|scored|grade|graded|rating|rated|marks?|stars?)\b", re.IGNORECASE),
    re.compile(r"(अंक|ग्रेड|रेटिंग|स्कोर|प्रतिशत)"),
    re.compile(r"(மதிப்பெண்|தரம்|சதவீதம்|ஸ்கோர்)"),
)


def check_no_scores(text: str) -> list[Violation]:
    plain = ascii_digits(text)
    if any(p.search(plain) for p in _PATTERNS):
        return [Violation("score_found", "a score, grade, rating or percentage")]
    return []
