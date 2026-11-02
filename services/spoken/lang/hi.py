# ruff: noqa: E501  (word tables and phrases are data, one entry a line)
"""Hindi pack. Own tables for 0 to 9999: no library. TODO-HUMAN(Seema): check every word and phrase.

0 to 99 reuse the list in services.speech.textnorm (one word per number, as Hindi has no regular
tens-and-units rule). Hundreds are "<digit> सौ", thousands "<n> हज़ार".
"""

from __future__ import annotations

from services.speech.textnorm import _HI_1_100  # one word for each number 0 to 100
from services.spoken.lang.base import LanguagePack


def number_to_words(n: int) -> str:
    if n < 0 or n > 9999:
        raise ValueError("0 to 9999")
    if n <= 99:
        return _HI_1_100[n]
    out: list[str] = []
    if n >= 1000:
        out.append(f"{_HI_1_100[n // 1000]} हज़ार")
        n %= 1000
    if n >= 100:
        out.append(f"{_HI_1_100[n // 100]} सौ")
        n %= 100
    if n:
        out.append(_HI_1_100[n])
    return " ".join(out)


HI = LanguagePack(
    code="hi",
    number_to_words=number_to_words,
    digit_words=tuple(_HI_1_100[:10]),
    math_words={
        "+": "जमा",
        "-": "घटा",
        "x": "गुणा",
        "/": "भाग",
        "=": "बराबर",
        "<": "से कम है",
        ">": "से ज़्यादा है",
        "%": "प्रतिशत",
        "point": "दशमलव",
    },
    ratio="{total} में से {n} {kids}",
    child_one="बच्चा",
    child_many="बच्चे",
    label_phrases={
        "सामग्री": "आपको चाहिए",
        "कदम": "कदम ये हैं",
        "उदाहरण": "उदाहरण के लिए",
        "रोल नंबर": "बच्चों के रोल नंबर",
    },
    ordinals=("पहला", "दूसरा", "तीसरा", "चौथा", "पाँचवाँ", "छठा", "सातवाँ", "आठवाँ", "नौवाँ", "दसवाँ"),
    phrases={
        "intro": "यह उन बच्चों के लिए है जो {what}",
        "of_class": "आपकी कक्षा में, {ratio}",
        "rolls": "रोल नंबर {list}",
        "rolls_possible": "संभावित, केवल एक प्रश्न में: रोल नंबर {list}",
        "and_more": "और {n} और",
        "and": "और",
        "why": "बच्चे ऐसा क्यों करते हैं।",
        "check": "दो मिनट की एक जाँच।",
        "strategies": "सिखाने के तरीके।",
        "activity": "दस मिनट की एक गतिविधि।",
        "mistakes": "सिखाते समय इन ग़लतियों से बचें।",
        "working": "कैसे पता चलेगा कि यह काम कर रहा है।",
        "home": "घर पर आज़माने के लिए कुछ।",
        "stuck": "अगर सुधार न हो।",
        "strategy": "तरीका {i}, {label}।",
        "materials": "आपको चाहिए {list}।",
        "step": "कदम {i}।",
        "example": "उदाहरण के लिए, {text}।",
        "example_say": "उदाहरण के लिए, जब आप {question} बोलते हैं, तो बच्चा {wrote} लिखता है। सही उत्तर {correct} है।",
        "working_line": "अगली जाँच में, इस ग़लती को इसके {n} या अधिक प्रश्नों में कम बच्चे करें। अभी, {ratio} करते हैं।",
    },
    script="devanagari",
)
