import dataclasses

import pytest

from engine.model import AnswerMark, ErrorCode, Item, ItemType, Mark


def test_error_codes_use_the_printed_names() -> None:
    assert [e.value for e in ErrorCode] == [
        "PV-HEARD",
        "PV-REVERSE",
        "ADD-NOCARRY",
        "SUB-SFL",
        "SUB-NODEC",
    ]


def test_item_types() -> None:
    assert {t.value for t in ItemType} == {"dictation", "add_carry", "sub_anchor", "sub_borrow"}


def test_items_and_marks_are_frozen() -> None:
    item = Item(n=1, type=ItemType.DICTATION, a=346)
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.a = 5  # type: ignore[misc]
    mark = AnswerMark(Mark.CORRECT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        mark.kind = Mark.OTHER  # type: ignore[misc]
