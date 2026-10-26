"""Class-number slots: the only way a number about a class may appear in track content.

A slot is written `{{name}}` in a template or draft and filled by code at delivery time, per
cohort (CLAUDE.md rule 1: code computes every number; the model never states one). The list is
closed: a draft that names any other slot is refused.
"""

from __future__ import annotations

# slot name -> where its value comes from (shown in the review queue so a reviewer sees it is code)
SLOT_SOURCES: dict[str, str] = {
    "class.count_showing": "engine: children who show this error (2-item rule)",
    "class.children_checked": "engine: children checked",
    "class.example_a": "engine: first number of the worked example for this error",
    "class.example_b": "engine: second number of the worked example (none for dictation errors)",
    "class.example_wrong_answer": "engine: the error function's wrong answer for the example",
    "class.example_correct_answer": "engine: the correct answer for the example",
    "track.error_name": "content/lang/error_names.yaml, in the teacher's language",
    "track.day": "the lesson's day in the track",
    "track.total_days": "the number of lessons in the track",
}
SLOT_NAMES: tuple[str, ...] = tuple(SLOT_SOURCES)
