"""The language pack interface: everything the normaliser needs that depends on the language.

A pack turns numbers into words, says digits one by one, names the math symbols, phrases "N of M",
gives the spoken form of screen labels and ordinals, and carries the few connecting phrases the
adapters use. Hindi and Tamil tables are first drafts: TODO-HUMAN(Seema: Hindi, Gopi: Tamil).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class NumberWords(Protocol):
    def __call__(self, n: int) -> str: ...


@dataclass(frozen=True)
class LanguagePack:
    code: str
    number_to_words: NumberWords  # 0 to 9999 (larger numbers are read digit by digit)
    digit_words: tuple[str, ...]  # "zero" ... "nine"
    math_words: dict[str, str]  # "+", "-", "x", "/", "=", "<", ">", "%", "point"
    ratio: str  # "{n} of {total}": uses {n} {total} {kids}, already worded
    child_one: str
    child_many: str
    label_phrases: dict[str, str]  # a screen label ("Materials") -> what is said ("You will need")
    ordinals: tuple[str, ...]  # first ... tenth
    phrases: dict[str, str] = field(default_factory=dict)  # connectors used by the adapters
    script: str = "latin"  # the script its own words are written in: latin | devanagari | tamil

    def digits_to_words(self, digits: str) -> str:
        return " ".join(self.digit_words[int(d)] for d in digits if d.isdigit())

    def ordinal(self, i: int) -> str:
        return self.ordinals[i - 1] if 1 <= i <= len(self.ordinals) else self.number_to_words(i)

    def ratio_phrase(self, n: int, total: int) -> str:
        kids = self.child_one if n == 1 else self.child_many
        return self.ratio.format(
            n=self.number_to_words(n), total=self.number_to_words(total), kids=kids
        )
