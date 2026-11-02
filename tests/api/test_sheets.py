# ruff: noqa: E501
"""Reading a sheet photo: blind read, code-side judging, privacy. A fake model, no network."""

from __future__ import annotations

import base64
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ai import config
from ai.audit import SqlAuditSink
from ai.calls.c08_answer_reading import CONFIDENCE_BAR, classify, plausible_answers
from ai.client import CallContext
from ai.schemas import SheetRead
from engine.bugs import correct_answer
from engine.forms import FORM_A
from services.api import practice as practice_api
from services.api import sheets as sheets_api
from services.api.main import app
from tests.support_ai import FakeClient

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
CORRECT = [str(correct_answer(i)) for i in FORM_A.items]


def good(**over: Any) -> SheetRead:
    reads = list(CORRECT)
    confs = [0.97] * 10
    for k, v in over.items():
        idx = int(k[1:]) - 1
        reads[idx], confs[idx] = v
    return SheetRead(reads=reads, confidences=confs)


@pytest.fixture
def make_client(sink: SqlAuditSink) -> Iterator[Any]:
    def build(*replies: Any) -> tuple[TestClient, FakeClient]:
        fake = FakeClient(list(replies))
        app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
            mode="stub", sink=sink, client=fake
        )
        return TestClient(app), fake

    yield build
    app.dependency_overrides.clear()


def post(client: TestClient, data: bytes = PNG, form: str = "A") -> Any:
    return client.post(
        "/api/sheets/read", files={"image": ("s.png", data, "image/png")}, data={"form": form}
    )


def test_confident_plausible_reads_are_ok_and_the_rest_wait_for_the_teacher() -> None:
    reads = list(CORRECT)
    confs = [0.97] * 10
    reads[1], confs[1] = "७२८", 0.9  # Devanagari digits are read as the digits they are
    reads[2], confs[2] = "999", 0.97  # confident but not an answer this item recognises
    reads[3], confs[3] = CORRECT[3], CONFIDENCE_BAR - 0.01  # a right-looking read, unsure
    reads[4], confs[4] = "", 0.95  # clearly blank
    reads[5], confs[5] = "", 0.0  # could not read
    reads[6], confs[6] = "x?", 0.9  # not digits
    cells = classify(FORM_A, reads, confs)
    assert [c.status for c in cells] == [
        "ok", "ok", "check", "check", "blank", "check", "check", "ok", "ok", "ok",
    ]  # fmt: skip
    assert cells[1].text == "728" and cells[2].text == "999" and cells[6].text == ""


def test_known_error_answers_are_plausible_so_an_error_is_not_sent_back_for_a_recheck() -> None:
    # item 3 is 38 + 47: 75 is the dropped-carry error answer, and 715 an untracked pattern
    assert {CORRECT[2], "75", "715"} <= plausible_answers(FORM_A, 2)
    assert "999" not in plausible_answers(FORM_A, 2)


def test_endpoint_returns_cells_and_never_the_photo(make_client: Any) -> None:
    client, fake = make_client(good(q3=("75", 0.95)))
    res = post(client)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["form"] == "A" and len(body["cells"]) == 10
    assert body["cells"][2] == {"text": "75", "status": "ok"}
    assert base64.b64encode(PNG).decode() not in res.text and "image" not in body
    assert len(fake.messages.calls) == 1


def test_a_box_of_number_words_is_turned_into_a_number_the_teacher_confirms(make_client: Any) -> None:
    # the photo: "three hundred five" and "four hundred ninety six" written in words (box 1 and 2)
    reply = good()
    reply.reads[0] = reply.reads[1] = ""
    reply.words = ["three hundred five", "four hundred - ninety six", *[""] * 8]
    reply.confidences[0] = reply.confidences[1] = 0.92
    client, _fake = make_client(reply)
    cells = post(client).json()["cells"]
    assert cells[0] == {"text": "305", "status": "check", "words": "three hundred five"}
    assert cells[1] == {"text": "496", "status": "check", "words": "four hundred - ninety six"}
    assert "words" not in cells[2]  # a box of digits is as before


def test_words_that_are_not_a_number_wait_for_the_teacher_with_nothing_filled_in() -> None:
    cells = classify(FORM_A, ["", *CORRECT[1:]], [0.9] * 10, ["three banana five", *[""] * 9])
    assert cells[0].text == "" and cells[0].status == "check" and cells[0].words == "three banana five"
    assert classify(FORM_A, CORRECT, [0.97] * 10, [])[0].status == "ok"  # no words: nothing changes


def test_a_words_list_of_the_wrong_length_or_with_digits_is_refused_and_retried(make_client: Any) -> None:
    bad = good()
    bad.words = ["305"]  # one entry, with digits
    client, fake = make_client(bad, good())
    cells = post(client).json()["cells"]
    assert len(fake.messages.calls) == 2  # the bad reply broke the rules, so the model was asked again
    assert cells[0]["status"] == "ok" and "words" not in cells[0]


def test_the_model_is_never_told_the_expected_answers(make_client: Any) -> None:
    client, fake = make_client(good())
    post(client)
    content = fake.messages.calls[0]["messages"][0]["content"]
    text = " ".join(p["text"] for p in content if p["type"] == "text")
    assert '"boxes": 10' in text
    for answer in CORRECT:
        assert answer not in text.replace('"boxes": 10', "")
    for item in FORM_A.items:
        assert f"{item.a}" not in text.replace('"boxes": 10', "")
    assert sum(1 for p in content if p["type"] == "image") == 1


def test_a_broken_first_read_is_retried_on_the_stronger_model(make_client: Any) -> None:
    broken = SheetRead(reads=["1"], confidences=[0.9])
    client, fake = make_client(broken, broken, good())
    res = post(client)
    assert res.status_code == 200 and res.json()["retried"] is True
    models = [c["model"] for c in fake.messages.calls]
    assert models[-1] == config.model_for("MODEL_READ_RETRY") and models[0] != models[-1]


def test_when_both_models_fail_she_is_told_to_type(make_client: Any) -> None:
    broken = SheetRead(reads=["1"], confidences=[0.9])
    client, _ = make_client(broken)
    res = post(client)
    assert res.status_code == 503 and res.json()["detail"]["needs_typing"] is True


def test_bad_uploads_are_refused_before_any_model_call(make_client: Any) -> None:
    client, fake = make_client(good())
    assert post(client, data=b"not an image at all").status_code == 422
    assert post(client, data=PNG + b"\x00" * (sheets_api.MAX_IMAGE_BYTES + 1)).status_code == 413
    assert post(client, form="Z").status_code == 422
    assert fake.messages.calls == []


def test_the_audit_row_holds_metadata_only_and_nothing_is_logged(
    make_client: Any, sink: SqlAuditSink, caplog: pytest.LogCaptureFixture
) -> None:
    client, _ = make_client(good())
    with caplog.at_level(logging.DEBUG):
        assert post(client).status_code == 200
    row = sink.recent(5)[0]
    assert row.call_key == "c08_answer_reading" and row.metadata_only is True
    blob = " ".join(r.getMessage() for r in caplog.records)
    assert base64.b64encode(PNG).decode()[:40] not in blob
    assert not any(a in blob for a in ("346", "728"))


def test_the_header_the_reader_saw_comes_back_to_the_phone(make_client: Any) -> None:
    from ai.schemas import SheetHeader

    reply = good()
    reply.header = SheetHeader(class_code="3A", roll_number=7, confidence=0.9)
    client, _ = make_client(reply)
    body = post(client).json()
    assert body["header"] == {"class_code": "3A", "roll_number": 7, "confidence": 0.9}


def test_no_header_is_null_and_the_file_hash_is_sent_only_when_it_is_valid(
    make_client: Any,
) -> None:
    client, fake = make_client(good(), good())
    res = client.post(
        "/api/sheets/read",
        files={"image": ("s.png", PNG, "image/png")},
        data={"form": "A", "sha256": "ab" * 32},
    )
    assert res.status_code == 200 and res.json()["header"] is None
    bad = client.post(
        "/api/sheets/read",
        files={"image": ("s.png", PNG, "image/png")},
        data={"form": "A", "sha256": "not-a-hash"},
    )
    assert bad.status_code == 200
    texts = [
        " ".join(p["text"] for p in c["messages"][0]["content"] if p["type"] == "text")
        for c in fake.messages.calls
    ]
    assert "file_sha256" in texts[0] and "file_sha256" not in texts[1]
