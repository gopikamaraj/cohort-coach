from __future__ import annotations

from services.spoken.lang.base import LanguagePack
from services.spoken.lang.en import EN
from services.spoken.lang.hi import HI
from services.spoken.lang.ta import TA

PACKS: dict[str, LanguagePack] = {"en": EN, "hi": HI, "ta": TA}


def pack_for(language: str) -> LanguagePack:
    return PACKS.get(language, EN)
