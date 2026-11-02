"""The pilot results page: written from a pair of checks, counts only, labelled a small pilot."""

from __future__ import annotations

import json
import re
from pathlib import Path

from engine.bugs import correct_answer, error_answers
from engine.forms import FORM_A, FORM_B
from engine.model import ErrorCode, Form
from scripts import pilot_results


def clean(form: Form) -> list[str]:
    return [str(correct_answer(i)) for i in form.items]


def sfl(form: Form) -> list[str]:
    row, made = clean(form), 0
    for k, item in enumerate(form.items):
        only = [
            w
            for w in sorted(error_answers(item).get(ErrorCode.SUB_SFL, frozenset()))
            if all(w not in v for c, v in error_answers(item).items() if c != ErrorCode.SUB_SFL)
        ]
        if made < 2 and only:
            row[k], made = str(only[0]), made + 1
    return row


def backup(tmp: Path, pre_rows: list[list[str]], post_rows: list[list[str]]) -> Path:
    data = {
        "format": "cohort-coach-backup",
        "classes": [{"id": "c-0123456789", "name": "3A", "simulated": False}],
        "checks": [
            {
                "id": "c-0123456789:1",
                "classId": "c-0123456789",
                "term": 1,
                "formKey": "A",
                "kind": "pre",
                "checkDate": "2026-10-26",
                "children": pre_rows,
                "updatedAt": 1,
                "absent": [3],
            },
            {
                "id": "c-0123456789:2",
                "classId": "c-0123456789",
                "term": 2,
                "formKey": "B",
                "kind": "post",
                "checkDate": "2026-11-30",
                "children": post_rows,
                "updatedAt": 2,
            },
        ],
    }
    f = tmp / "backup.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_with_no_backup_it_says_there_is_nothing_yet_and_shows_no_number(tmp_path: Path) -> None:
    out = tmp_path / "r.md"
    assert pilot_results.main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "No pre-test and post-test pair" in text
    assert not re.search(r"\| *\d", text)


def test_a_pair_gives_counts_per_competency_labels_and_a_small_sample_note(tmp_path: Path) -> None:
    pre = [sfl(FORM_A), sfl(FORM_A), clean(FORM_A), clean(FORM_A)]
    post = [clean(FORM_B), sfl(FORM_B), clean(FORM_B), clean(FORM_B)]
    out = tmp_path / "r.md"
    assert pilot_results.main([str(backup(tmp_path, pre, post)), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Pre-test Form A (2026-10-26) to Post-test Form B (2026-11-30)" in text
    assert "A small pilot" in text and "3 children paired" in text and "1 away" in text
    assert "| C3 Taking away with borrowing | 2 | 1 | 1 | 0 |" in text
    assert "read this as directional only" in text


def test_the_page_never_holds_an_answer_a_class_id_or_a_roll_position(tmp_path: Path) -> None:
    pre = [sfl(FORM_A)] * 12
    post = [clean(FORM_B)] * 12
    out = tmp_path / "r.md"
    pilot_results.main([str(backup(tmp_path, pre, post)), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "c-0123456789" not in text
    for row in (pre[0], post[0]):
        assert ",".join(row) not in text and " ".join(row) not in text
    assert "directional" not in text  # 12 paired is not a small sample
