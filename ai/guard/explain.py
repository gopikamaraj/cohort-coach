"""One-line reasons for every AI decision a user sees, built by code from facts already computed.

Teacher-facing lines use counts ("11 of 28 children"), never percentages. Hindi and Tamil
wording is a first draft: TODO-HUMAN(Seema, Gopi): native review.
"""

from __future__ import annotations

from typing import Any

from ai.validators._data import load_yaml

TEMPLATES: dict[str, dict[str, str]] = {
    "grouped": {
        "en": "Grouped for {error} because {showing} of {checked} children showed it.",
        "hi": "{error} के लिए जोड़ा गया, क्योंकि {checked} में से {showing} बच्चों में यह दिखा।",
        "ta": "{error} பயிற்சிக்குச் சேர்க்கப்பட்டது, ஏனெனில் {checked} குழந்தைகளில் {showing} பேரிடம் இது தெரிந்தது.",
    },
    "held_maths": {
        "en": "Held back: the checker found a maths error.",
        "hi": "रोका गया: जाँच में गणित की गलती मिली।",
        "ta": "நிறுத்தப்பட்டது: சரிபார்ப்பில் கணக்குப் பிழை கண்டறியப்பட்டது.",
    },
    "held_number": {
        "en": "Held back: a number did not match what the engine chose.",
        "hi": "रोका गया: एक संख्या इंजन की चुनी संख्या से नहीं मिली।",
        "ta": "நிறுத்தப்பட்டது: ஒரு எண் இயந்திரம் தேர்ந்தெடுத்த எண்ணுடன் பொருந்தவில்லை.",
    },
    "held_quote": {
        "en": "Held back: a quote was not in what you said.",
        "hi": "रोका गया: एक उद्धरण आपके कहे में नहीं मिला।",
        "ta": "நிறுத்தப்பட்டது: ஒரு மேற்கோள் நீங்கள் சொன்னதில் இல்லை.",
    },
    "held_slots": {
        "en": "Held back: a class number was written out instead of coming from a slot.",
        "hi": "रोका गया: कक्षा की एक संख्या स्लॉट से आने की जगह सीधे लिखी गई थी।",
        "ta": "நிறுத்தப்பட்டது: வகுப்பின் ஒரு எண் இடத்தின் மூலம் வராமல் நேரடியாக எழுதப்பட்டது.",
    },
    "held_check_item": {
        "en": "Held back: it used an item from the pilot test, which a lesson must never do.",
        "hi": "रोका गया: इसमें पायलट परीक्षा का एक प्रश्न था, जो किसी पाठ में नहीं होना चाहिए।",
        "ta": "நிறுத்தப்பட்டது: இதில் பைலட் தேர்வின் ஒரு கேள்வி இருந்தது; பாடத்தில் அது இருக்கக்கூடாது.",
    },
    "held_filter": {
        "en": "Held back: the safety filter stopped this text.",
        "hi": "रोका गया: सुरक्षा फ़िल्टर ने इस पाठ को रोक दिया।",
        "ta": "நிறுத்தப்பட்டது: பாதுகாப்பு வடிகட்டி இந்த உரையை நிறுத்தியது.",
    },
    "held_language": {
        "en": "Held back: the text was not in the right language.",
        "hi": "रोका गया: पाठ सही भाषा में नहीं था।",
        "ta": "நிறுத்தப்பட்டது: உரை சரியான மொழியில் இல்லை.",
    },
    "held_reading": {
        "en": "Held back: the wording was too hard for the audience.",
        "hi": "रोका गया: शब्द इस पाठक के लिए बहुत कठिन थे।",
        "ta": "நிறுத்தப்பட்டது: சொற்கள் வாசிப்பவருக்கு மிகக் கடினமாக இருந்தன.",
    },
    "held_checker": {
        "en": "Held back: the checker did not pass it ({reason}).",
        "hi": "रोका गया: जाँचकर्ता ने इसे पास नहीं किया ({reason})।",
        "ta": "நிறுத்தப்பட்டது: சரிபார்ப்பு இதை ஏற்கவில்லை ({reason}).",
    },
    "held_checker_down": {
        "en": "Held back: it could not be checked, so a person will look first.",
        "hi": "रोका गया: जाँच नहीं हो सकी, इसलिए पहले कोई व्यक्ति देखेगा।",
        "ta": "நிறுத்தப்பட்டது: சரிபார்க்க முடியவில்லை, அதனால் முதலில் ஒருவர் பார்ப்பார்.",
    },
    "waiting_review": {
        "en": "Checked by code and the checker. Waiting for a reviewer.",
        "hi": "कोड और जाँचकर्ता ने जाँचा। समीक्षक का इंतज़ार है।",
        "ta": "குறியீடும் சரிபார்ப்பும் சோதித்தன. மதிப்பாய்வாளருக்காகக் காத்திருக்கிறது.",
    },
    "passed": {
        "en": "Passed the code checks and the checker.",
        "hi": "कोड जाँच और जाँचकर्ता दोनों में पास।",
        "ta": "குறியீட்டுச் சோதனையும் சரிபார்ப்பும் ஏற்றன.",
    },
    "passed_reviewed": {
        "en": "Passed the code checks and the checker, and a reviewer approved it.",
        "hi": "कोड जाँच और जाँचकर्ता में पास, और समीक्षक ने मंज़ूर किया।",
        "ta": "குறியீட்டுச் சோதனையும் சரிபார்ப்பும் ஏற்றன, மதிப்பாய்வாளரும் ஒப்புதல் அளித்தார்.",
    },
}

LANGS = ("en", "hi", "ta")


def error_name(error: str, lang: str) -> str:
    return str(load_yaml("lang/error_names.yaml")[error][lang])


def explain(key: str, lang: str, **facts: Any) -> str:
    """Render one reason. Facts are plain values (counts, names) computed by code."""
    return TEMPLATES[key][lang].format(**facts)


def explain_grouped(error: str, showing: int, checked: int, lang: str) -> str:
    if checked <= 0 or not 0 <= showing <= checked:
        raise ValueError("counts must satisfy 0 <= showing <= checked, checked > 0")
    return explain("grouped", lang, error=error_name(error, lang), showing=showing, checked=checked)
