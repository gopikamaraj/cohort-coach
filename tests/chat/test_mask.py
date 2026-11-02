"""C02: masking. Names, roll numbers, relatives, phone numbers and emails are replaced before any
model sees the text or any person reads it; a second check runs on what a model writes."""

from __future__ import annotations

import pytest

from ai.validators.mask import check_masked, mask_personal


@pytest.mark.parametrize(
    "text,gone",
    [
        ("Meena keeps writing 403 for 43. What do I do?", "Meena"),
        ("मीना हमेशा 403 लिखती है, क्या करूँ?", "मीना"),
        ("மீனாவுக்கு 43 என்றால் 403 என்று எழுதுகிறாள்", "மீனா"),
        ("Rahul's sister cannot subtract.", "Rahul"),
        ("roll no 14 writes 37 for 52 - 29", "roll no 14"),
        ("Call me on 9876543210 about it", "9876543210"),
        ("Mail ravi.kumar@example.com the sheet", "ravi.kumar@example.com"),
    ],
)
def test_personal_data_is_replaced_and_what_is_left_passes_the_second_check(
    text: str, gone: str
) -> None:
    masked = mask_personal(text)
    assert gone not in masked.text
    assert masked.kinds
    assert check_masked(masked.text) == []


def test_the_kinds_are_codes_never_the_matched_text() -> None:
    masked = mask_personal("Meena and roll no 14, call 9876543210")
    assert set(masked.kinds) == {"child_name", "roll_number", "phone_or_id"}
    assert "Meena" not in " ".join(masked.kinds)


def test_a_child_is_marked_so_the_question_can_be_routed() -> None:
    assert mask_personal("Meena writes 403").child_mentioned
    assert mask_personal("roll no 7 is slow").child_mentioned
    assert mask_personal("Rahul's brother is slow").child_mentioned
    assert not mask_personal("Call 9876543210").child_mentioned


@pytest.mark.parametrize(
    "text",
    [
        "How do I show 52 minus 29 with bundles of ten sticks?",
        "What does check by adding back mean?",
        "बच्चे 52 में से 29 कैसे घटाएँ?",
        "10 sticks make a bundle. 5 bundles and 2 sticks is 52.",
    ],
)
def test_an_ordinary_maths_question_is_left_alone(text: str) -> None:
    masked = mask_personal(text)
    assert masked.text == text and masked.kinds == ()


def test_a_name_inside_an_ordinary_word_is_not_masked() -> None:
    # "anu" is a name; "anushasan" (discipline), "अनुभव" (experience), "அனுபவம்" are not it
    assert mask_personal("anushasan matters").text == "anushasan matters"
    assert mask_personal("अनुभव से सीखो").kinds == ()
    assert mask_personal("அனுபவம் முக்கியம்").kinds == ()


def test_the_second_layer_catches_a_name_a_model_wrote() -> None:
    codes = [v.code for v in check_masked("Tell Meena to open a bundle.")]
    assert "child_name" in codes
    assert [v.code for v in check_masked("Call 9876543210")] == ["pii_phone"]
    assert check_masked("Open a bundle to get ten loose sticks.") == []


def test_the_masked_text_has_no_raw_name_even_with_many_names() -> None:
    masked = mask_personal("Meena, Ravi and Anu all write 403; Ravi's mother says so")
    for name in ("Meena", "Ravi", "Anu"):
        assert name not in masked.text


def test_names_in_keep_are_left_and_every_other_name_is_still_masked() -> None:
    # The Practice Class's five children are fictional: their names stay, a real child's does not.
    masked = mask_personal("Priya, what is 52 minus 29? Rahul got 37.", keep=("Priya", "Arun"))
    assert "Priya" in masked.text and "Rahul" not in masked.text
    assert masked.kinds == ("child_name",)
    assert "52 minus 29" in masked.text
    tamil = mask_personal("ப்ரியாவுக்கு 52 கழித்தல் 29", keep=("ப்ரியா",))
    assert "ப்ரியா" in tamil.text
