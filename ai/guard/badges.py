"""Checked and Reviewed badges.

Checked ✓ means gates 1 and 2 passed (code checks, pre-filter, call 7). Checked ✓ · Reviewed ✓
means gate 3 (a human) approved too. Telegram lessons carry the badge line in her language.
"""

from __future__ import annotations

from enum import StrEnum


class Badge(StrEnum):
    NONE = "none"
    CHECKED = "checked"
    CHECKED_REVIEWED = "checked_reviewed"


# TODO-HUMAN(Seema, Gopi): native review of the hi and ta wording.
_CHECKED = {"en": "Checked ✓", "hi": "जाँचा गया ✓", "ta": "சரிபார்க்கப்பட்டது ✓"}
_REVIEWED = {"en": "Reviewed ✓", "hi": "समीक्षित ✓", "ta": "மதிப்பாய்வு செய்யப்பட்டது ✓"}


def compute_badge(*, gates_1_2_passed: bool, human_approved: bool) -> Badge:
    if not gates_1_2_passed:
        return Badge.NONE  # a human cannot lift a failed automatic gate into a badge
    return Badge.CHECKED_REVIEWED if human_approved else Badge.CHECKED


def badge_line(badge: Badge, lang: str) -> str:
    if badge is Badge.NONE:
        return ""
    if badge is Badge.CHECKED:
        return _CHECKED[lang]
    return f"{_CHECKED[lang]} · {_REVIEWED[lang]}"
