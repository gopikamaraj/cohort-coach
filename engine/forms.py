"""The two printed pilot forms. Numbers only: every answer is computed by `engine.bugs`.

tests/engine/test_forms.py proves each item reproduces docs/design/pilot_forms.golden.json.
"""

from __future__ import annotations

from engine.model import Form, Item, ItemType

_D, _A, _S, _B = (
    ItemType.DICTATION,
    ItemType.ADD_CARRY,
    ItemType.SUB_ANCHOR,
    ItemType.SUB_BORROW,
)

FORM_A = Form(
    "Pre-test · Form A",
    (
        Item(1, _D, 346),
        Item(2, _D, 728),
        Item(3, _A, 38, 47),
        Item(4, _A, 46, 28),
        Item(5, _A, 59, 23),
        Item(6, _S, 87, 52),
        Item(7, _B, 74, 36),
        Item(8, _B, 45, 19),
        Item(9, _B, 82, 39),
        Item(10, _B, 81, 27),
    ),
)

FORM_B = Form(
    "Post-test · Form B",
    (
        Item(1, _D, 264),
        Item(2, _D, 853),
        Item(3, _A, 29, 46),
        Item(4, _A, 35, 49),
        Item(5, _A, 18, 54),
        Item(6, _S, 86, 41),
        Item(7, _B, 83, 35),
        Item(8, _B, 64, 28),
        Item(9, _B, 71, 18),
        Item(10, _B, 93, 29),
    ),
)

PILOT_FORMS: dict[str, Form] = {"A": FORM_A, "B": FORM_B}
