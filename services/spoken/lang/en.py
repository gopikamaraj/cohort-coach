# ruff: noqa: E501  (word tables and phrases are data, one entry a line)
"""English pack: num2words for the numbers."""

from __future__ import annotations

from num2words import num2words

from services.spoken.lang.base import LanguagePack

_DIGITS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def number_to_words(n: int) -> str:
    return str(num2words(n, lang="en")).replace(",", "")


EN = LanguagePack(
    code="en",
    number_to_words=number_to_words,
    digit_words=_DIGITS,
    math_words={
        "+": "plus",
        "-": "minus",
        "x": "times",
        "/": "divided by",
        "=": "equals",
        "<": "is less than",
        ">": "is more than",
        "%": "percent",
        "point": "point",
    },
    ratio="{n} {kids} out of {total}",
    child_one="child",
    child_many="children",
    label_phrases={
        "materials": "You will need",
        "steps": "The steps are",
        "worked example": "For example",
        "example from your class": "An example from your class",
        "roll numbers": "The children are on roll numbers",
    },
    ordinals=(
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
    ),
    phrases={
        "intro": "This is for the children who {what}",
        "of_class": "In your class, {ratio}",
        "rolls": "Roll numbers {list}",
        "rolls_possible": "Possible, on one question only: roll numbers {list}",
        "and_more": "and {n} more",
        "and": "and",
        "why": "Why children do this.",
        "check": "A two-minute check you can do.",
        "strategies": "Ways to teach it.",
        "activity": "A ten-minute activity.",
        "mistakes": "Mistakes to avoid when teaching it.",
        "working": "How you will know it is working.",
        "home": "Something to try at home.",
        "stuck": "If it is not improving.",
        "strategy": "Way {i}, {label}.",
        "materials": "You will need {list}.",
        "step": "Step {i}.",
        "example": "For example, {text}.",
        "example_say": "For example, when you say {question}, a child writes {wrote}. The right answer is {correct}.",
        "working_line": "At the next check, fewer children should make this mistake on {n} or more of its questions. For now, {ratio} make it.",
    },
)
