"""POST /api/stages: class counts per (error, stage) from reads held for this request only."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)

CORE = [346, 728, 85, 74, 82, 35, 42, 34, 57, 66]  # SUB-SFL on items 7 to 10
OUTPUT = [346, 728, 58, 47, 28, 35, 83, 62, 43, 54]  # answers reversed
CLEAN = [346, 728, 85, 74, 82, 35, 38, 26, 43, 54]


def post(children: list[dict], form: str = "A", lang: str = "en"):  # type: ignore[type-arg]
    return client.post("/api/stages", json={"form": form, "language": lang, "children": children})


def kid(answers: list, **kw: object) -> dict:  # type: ignore[type-arg]
    return {"answers": answers, **kw}


def test_counts_per_error_and_stage_with_a_probe_for_each_stage() -> None:
    r = post([kid(CORE), kid(CORE), kid(OUTPUT), kid(CLEAN)])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checked"] == 4 and body["missed_teaching"] == 0
    sig = {(s["code"], s["stage"]): s["n"] for s in body["by_signature"]}
    assert sig[("SUB-SFL", "Core")] == 2 and sig[("OUT-REV", "Output")] == 1
    stages = {s["stage"]: s["n"] for s in body["by_stage"]}
    assert stages == {"Core": 2, "Output": 1}
    assert all(body["probes"][s] for s in stages)  # a one-minute probe on every stage line
    assert "most likely" in body["note"].lower()


def test_children_tagged_missed_the_teaching_are_counted_apart_from_core() -> None:
    body = post([kid(CORE), kid(CORE, missed_teaching=True)]).json()
    assert body["checked"] == 2 and body["missed_teaching"] == 1
    assert {s["stage"]: s["n"] for s in body["by_stage"]} == {"Core": 1}


def test_blank_and_unreadable_marks_are_accepted() -> None:
    r = post([kid([346, 728, "blank", "blank", "blank", 35, 38, "blank", "blank", "blank"])])
    assert r.status_code == 200 and r.json()["not_attempted"] == 1


def test_unreadable_boxes_count_toward_the_output_signature() -> None:
    answers = [346, 728, 85, 74, "unreadable", 35, "unreadable", 26, 43, 54]
    r = post([kid(answers)])
    assert {s["code"] for s in r.json()["by_signature"]} == {"OUT-REC"}


def test_the_response_holds_no_per_child_data() -> None:
    body = post([kid(CORE)]).json()
    assert set(body) == {
        "checked",
        "missed_teaching",
        "not_attempted",
        "missed_by_concept",
        "by_signature",
        "by_stage",
        "probes",
        "note",
    }
    assert '"answers"' not in json.dumps(body)  # no per-child rows come back


def test_nothing_about_the_children_reaches_the_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        post([kid([346, 728, 85, 74, 82, 35, 42, 34, 57, 66])])
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "57, 66" not in text and "answers" not in text


@pytest.mark.parametrize(
    "children",
    [
        [kid([1, 2, 3])],  # wrong length
        [kid([1] * 10 + [2])],
        [kid(["abc"] + [1] * 9)],
        [],
        [kid(CLEAN)] * 301,
    ],
)
def test_bad_input_is_refused(children: list) -> None:  # type: ignore[type-arg]
    assert post(children).status_code == 422


def test_an_unknown_form_or_language_is_refused() -> None:
    assert post([kid(CLEAN)], form="Z").status_code == 422
    assert post([kid(CLEAN)], lang="fr").status_code == 422


def test_form_b_uses_form_b_items() -> None:
    r = post([kid([264, 853, 17, 14, 72, 45, 48, 36, 53, 64])] * 2, form="B")
    assert {s["code"] for s in r.json()["by_signature"]} == {"IN-OP"}
