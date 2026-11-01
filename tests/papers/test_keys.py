"""A paper's own key is the engine's key for the paper's numbers, the same shape the phone reads."""

from __future__ import annotations

from engine.export_keys import build_answer_keys
from engine.forms import FORM_A
from engine.model import ItemType
from services.papers import keys


def body_of_form_a() -> dict:
    ops = {
        ItemType.DICTATION: "dictate",
        ItemType.ADD_CARRY: "add",
        ItemType.SUB_ANCHOR: "subtract",
        ItemType.SUB_BORROW: "subtract",
    }
    return {
        "items": [{"n": i.n, "operation": ops[i.type], "a": i.a, "b": i.b} for i in FORM_A.items]
    }


def test_a_paper_with_the_numbers_of_a_built_in_form_gets_the_same_key() -> None:
    mine = keys.key_of("P-000000000001", body_of_form_a(), "x")["forms"]["P-000000000001"]
    built_in = build_answer_keys()["forms"]["A"]
    # answers, wrong answers, probes and signatures are the same; a paper's key also marks anchors
    same = [{k: v for k, v in i.items() if k != "anchor"} for i in mine["items"]]
    assert same == built_in["items"]
    assert all(i["anchor"] for i in mine["items"])


def test_the_item_type_follows_from_the_numbers() -> None:
    form = keys.form_of(body_of_form_a(), "x")
    assert [i.type for i in form.items] == [i.type for i in FORM_A.items]


def test_each_item_says_whether_it_is_an_anchor() -> None:
    body = body_of_form_a()
    body["items"][9]["is_anchor"] = False
    items = keys.key_of("P-000000000003", body, "x")["forms"]["P-000000000003"]["items"]
    assert [i["anchor"] for i in items] == [True] * 9 + [False]


def test_extra_items_are_part_of_the_key() -> None:
    body = body_of_form_a()
    body["items"].append({"n": 11, "operation": "subtract", "a": 61, "b": 28})
    form = keys.key_of("P-000000000002", body, "x")["forms"]["P-000000000002"]
    assert len(form["items"]) == 11 and form["items"][10]["correct"] == 33
