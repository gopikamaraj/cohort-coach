"""The importer's code side: the AI reads, code computes, a person confirms. Recorded reads only."""

from __future__ import annotations

from ai.schemas import PaperRead, ReadPaperItem
from services.papers_hub import importer as imp


def item(n: int, op: str, a: int | None, b: int | None = None, **kw: object) -> ReadPaperItem:
    return ReadPaperItem(n=n, operation=op, a=a, b=b, **kw)  # type: ignore[arg-type]


def pilot_read(**kw: object) -> PaperRead:
    items = [
        item(1, "dictate", None),
        item(2, "dictate", None),
        item(3, "add", 38, 47),
        item(4, "add", 46, 28),
        item(5, "add", 59, 23),
        item(6, "subtract", 87, 52),
        item(7, "subtract", 74, 36),
        item(8, "subtract", 45, 19),
        item(9, "subtract", 82, 39),
        item(10, "subtract", 81, 27),
        item(11, "add", 246, 178),
        item(12, "subtract", 786, 452),
    ]
    return PaperRead(form_letter="A", check_code="3B-04", class_code="3B", items=items, **kw)  # type: ignore[arg-type]


def draft_of(*reads: PaperRead) -> dict:
    return imp.recompute(imp.merge(list(reads)))


def by_n(draft: dict, n: int) -> dict:
    return next(i for i in draft["items"] if i["n"] == n)


def test_code_computes_every_key_and_the_ai_is_never_asked_for_one() -> None:
    d = draft_of(pilot_read())
    assert by_n(d, 3)["correct"] == 85 and by_n(d, 7)["correct"] == 38
    assert by_n(d, 12)["correct"] == 334 and by_n(d, 11)["correct"] == 424
    assert "correct" not in ReadPaperItem.model_fields  # the schema has no field for an answer


def test_probes_and_wrong_answers_come_from_the_engines_bug_functions() -> None:
    d = draft_of(pilot_read())
    assert by_n(d, 3)["error_probes"] == ["ADD-NOCARRY"] and by_n(d, 3)["wrong"] == {
        "ADD-NOCARRY": [75]
    }
    assert set(by_n(d, 7)["error_probes"]) == {"SUB-SFL", "SUB-NODEC"}
    assert by_n(d, 7)["wrong"] == {"SUB-SFL": [42], "SUB-NODEC": [48]}


def test_a_dictated_item_needs_the_number_said_and_is_never_guessed() -> None:
    d = draft_of(pilot_read())
    one = by_n(d, 1)
    assert (
        not one["supported"]
        and one["reason"] == "dictated_number_needed"
        and one["include"] is False
    )
    assert any(q["id"] == "dictation-1" and not q["blocking"] for q in d["open_questions"])
    d["items"][0]["a"] = 346
    d = imp.recompute(d)
    assert by_n(d, 1)["supported"] and by_n(d, 1)["correct"] == 346
    assert by_n(d, 1)["wrong"]["PV-HEARD"] == [3046, 30046, 300406]


def test_unsupported_items_are_listed_and_can_be_left_out() -> None:
    read = pilot_read()
    read.items.append(item(13, "other", None, prompt_text="A rope is 12 m long"))
    read.items.append(item(14, "add", 800, 400))  # sum over 999
    d = draft_of(read)
    assert by_n(d, 13)["reason"] == "not_a_supported_type" and not by_n(d, 13)["include"]
    assert by_n(d, 14)["reason"] == "sum_over_999"
    assert {q["id"] for q in d["open_questions"]} >= {"unsupported-13", "unsupported-14"}


def test_a_printed_key_that_differs_is_flagged_and_blocks_confirm_until_acknowledged() -> None:
    read = pilot_read()
    read.items[2] = item(3, "add", 38, 47, printed_answer="75")  # the key printed 75; the sum is 85
    d = draft_of(read)
    assert by_n(d, 3)["key_mismatch"] and by_n(d, 3)["correct"] == 85
    assert any(q["id"] == "key-3" and q["blocking"] for q in d["open_questions"])
    d["items"][2]["acknowledged"] = True
    assert not any(q["id"] == "key-3" for q in imp.recompute(d)["open_questions"])


def test_handwriting_means_no_printed_answer_is_kept() -> None:
    read = pilot_read(contains_handwritten_answers=True)
    read.items[2] = item(3, "add", 38, 47, printed_answer="85")  # a child's answer, not a key
    d = draft_of(read)
    assert by_n(d, 3)["printed_answer"] is None and not by_n(d, 3)["key_mismatch"]
    assert d["contains_handwritten_answers"] is True


def test_a_misread_number_can_be_fixed_and_everything_is_recomputed() -> None:
    read = pilot_read()
    read.items[5] = item(6, "subtract", 87, 62, unsure=True)  # working marks hid the 5
    d = draft_of(read)
    assert by_n(d, 6)["unsure"] and any(
        q["id"] == "unsure-6" and q["blocking"] for q in d["open_questions"]
    )
    d["items"][5].update(b=52, unsure=False)
    d = imp.recompute(d)
    assert by_n(d, 6)["correct"] == 35 and not any(
        q["id"] == "unsure-6" for q in d["open_questions"]
    )


def test_two_photos_of_one_paper_merge_by_item_number_and_flag_a_disagreement() -> None:
    a, b = pilot_read(), pilot_read()
    b.items[3] = item(4, "add", 46, 29)  # operand hidden by a mark on one photo
    d = draft_of(a, b)
    assert d["sheets_read"] == 2 and by_n(d, 4)["disagreement"] and by_n(d, 4)["unsure"]
    assert not by_n(d, 3)["disagreement"]


def test_coverage_grid_and_a_warning_when_an_error_has_fewer_than_two_items() -> None:
    d = draft_of(pilot_read())
    assert d["coverage"]["ADD-NOCARRY"] == [3, 4, 5, 11]
    assert 6 not in d["coverage"]["SUB-SFL"] and 7 in d["coverage"]["SUB-SFL"]
    assert "PV-HEARD" in d["coverage_warnings"]  # the dictated items have no number yet
    for it in d["items"]:
        if it["include"] and it["operation"] != "dictate":
            assert it["include"] is True


def test_confirm_stays_blocked_until_class_and_kind_are_chosen() -> None:
    d = draft_of(pilot_read())
    ids = {q["id"] for q in imp.blocking(d)}
    assert {"class", "kind"} <= ids and "form" not in ids  # the form letter follows from the kind
    d.update(class_id="c-1", kind="pre", form="A")
    assert not imp.blocking(imp.recompute(d))


def test_the_independent_arithmetic_agrees_with_the_engine_on_every_supported_pair() -> None:
    for a in range(1, 120, 7):
        for b in range(0, a, 11):
            it = imp.compute_item(item(1, "subtract", a, b), drop_printed_answer=True)
            assert it["correct"] == a - b and not it["findings"]


def test_a_teachers_guide_fills_the_dictated_numbers_and_never_adds_a_question() -> None:
    from ai.schemas import PaperRead, ReadPaperItem
    from services.papers_hub import importer as imp

    paper = PaperRead(
        items=[
            ReadPaperItem(n=1, operation="dictate"),
            ReadPaperItem(n=2, operation="dictate"),
            ReadPaperItem(n=3, operation="add", a=38, b=47),
        ]
    )
    guide = PaperRead(
        items=[
            ReadPaperItem(n=1, operation="dictate", a=346),
            ReadPaperItem(n=2, operation="dictate", a=728),
            ReadPaperItem(n=9, operation="dictate", a=555),  # not on the paper: ignored
        ]
    )
    plain = imp.recompute(imp.merge([paper]))
    assert [i["reason"] for i in plain["items"][:2]] == ["dictated_number_needed"] * 2
    out = imp.recompute(imp.merge([paper], [guide]))
    assert [i["n"] for i in out["items"]] == [1, 2, 3]
    first = out["items"][0]
    assert (first["a"], first["supported"], first["from_guide"], first["correct"]) == (
        346,
        True,
        True,
        346,
    )
    assert out["items"][1]["a"] == 728 and out["items"][2]["from_guide"] is False


def test_files_keep_their_roles_and_the_paper_comes_first() -> None:
    import io

    from PIL import Image

    from services.papers_hub import service as svc

    def jpeg(c: int) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (40, 40), (c, c, c)).save(buf, "JPEG")
        return buf.getvalue()

    pages = svc.render_pages(
        [("g.jpg", jpeg(10)), ("p.jpg", jpeg(200)), ("x.jpg", jpeg(90))],
        ["guide", "paper", "other"],
    )
    assert [r for r, _ in pages] == ["paper", "guide", "other"]
    import pytest

    with pytest.raises(svc.Invalid):
        svc.render_pages([("a.jpg", jpeg(1))] * 7)


def test_an_answer_key_file_cross_checks_and_fills_dictation_but_never_sets_an_answer() -> None:
    import pytest

    from ai.schemas import PaperRead, ReadPaperItem
    from services.papers_hub import importer as imp
    from services.papers_hub import service as svc

    paper = PaperRead(
        items=[
            ReadPaperItem(n=1, operation="dictate"),
            ReadPaperItem(n=3, operation="add", a=38, b=47),
            ReadPaperItem(n=4, operation="add", a=46, b=28),
        ]
    )
    out = imp.recompute(imp.merge([paper], key={1: 305, 3: 85, 4: 99, 9: 1}))
    first, third, fourth = out["items"]
    assert (first["a"], first["from_key"], first["supported"]) == (305, True, True)
    assert third["key_file"] == 85 and third["key_mismatch"] is False and third["correct"] == 85
    assert fourth["key_mismatch"] is True and fourth["correct"] == 74  # code's answer stands
    assert [i["n"] for i in out["items"]] == [1, 3, 4]  # the key adds no question
    assert svc.parse_key('{"answers": {"1": 305, "3": 85}}') == {1: 305, 3: 85}
    assert svc.parse_key("") == {}
    bad_keys = (
        "nope",
        '{"answers": {"1": 5000}}',
        '{"answers": {"99": 5}}',
        '{"answers": {"1": "x"}}',
    )
    for bad in bad_keys:
        with pytest.raises(svc.Invalid):
            svc.parse_key(bad)
