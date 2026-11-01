"""Each simulated child has a sprite persona and a face chosen by code; the first seating leaks
nothing; recorded runs get faces from their recorded facts."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.sprites.avatar import expression_ids, personas
from services.practice.faces import persona_id
from services.practice.watch import load_recorded
from tests.practice.test_api import client, create  # noqa: F401  (the fixture)

EXPRESSIONS = set(expression_ids())


def test_every_practice_persona_has_a_sprite_persona() -> None:
    from services.practice.content import load_personas

    ids = {k.id for k in load_personas().children}
    assert ids <= set(personas())


def test_the_first_seating_names_a_persona_and_a_calm_face_and_leaks_nothing(
    client: TestClient,  # noqa: F811
) -> None:
    body = create(client)
    kids = body["children"]
    assert len(kids) == 5 and all(k["persona"] in personas() for k in kids)
    assert {k["expression"] for k in kids} <= {"neutral", "shy"}
    for k in kids:  # the shy child looks shy; nobody looks like they hold the mistake
        assert (k["expression"] == "shy") == k["shy"]
    assert not {"level", "band", "has_error"} & set(kids[0])


def test_a_turn_gives_every_child_a_registered_face_and_marks_the_speaker(
    client: TestClient,  # noqa: F811
) -> None:
    s = create(client)
    name = s["children"][1]["name"]
    res = client.post(
        f"/api/practice/sessions/{s['session_id']}/turns",
        json={"text": f"{name}, what is 52 minus 29?"},
    ).json()
    kids = res["children"]
    assert {k["expression"] for k in kids} <= EXPRESSIONS
    said = [res["speaker"], *[o["speaker"] for o in res["others"]]] if res["speaker"] else []
    assert sorted(k["name"] for k in kids if k["speaking"]) == sorted(said)  # everyone who spoke
    assert all(k["persona"] in personas() for k in kids)


def test_a_wrong_answer_shows_a_wrong_answer_face_and_the_face_is_not_a_number(
    client: TestClient,  # noqa: F811
) -> None:
    s = create(client)
    name = s["children"][1]["name"]
    res = client.post(
        f"/api/practice/sessions/{s['session_id']}/turns",
        json={"text": f"{name}, what is 52 minus 29?"},
    ).json()
    speaker = next(k for k in res["children"] if k["name"] == res["speaker"])
    assert res["intent"] == "answer"
    assert speaker["expression"] in {"wrong_answer", "got_it"}
    assert (speaker["expression"] == "wrong_answer") == (
        res["layers"]["processing"]["engine"]["correct"] is False
    )


@pytest.mark.parametrize("style", ["experienced", "struggling"])
@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_recorded_runs_get_faces_from_their_recorded_facts(style: str, lang: str) -> None:
    run = load_recorded("SUB-SFL", style, lang)
    assert run is not None
    for turn in run["turns"]:
        for c in turn["children"]:
            assert c["persona"] == persona_id(c["name"], lang) and c["persona"] in personas()
            assert c["expression"] in EXPRESSIONS
            assert c["speaking"] == (c["name"] == turn["child"]["speaker"])


def test_the_tray_is_drawn_from_sprite_items_of_the_enabled_pack(
    client: TestClient,  # noqa: F811
) -> None:
    from services.api.sprites.items import item_ids

    body = create(client)
    assert body["material_items"] == {
        "bundles": "bundle_of_ten",
        "sticks": "stick",
        "chart": "ten_frame",
    }
    assert set(body["material_items"].values()) <= set(item_ids())


def test_a_pack_that_is_not_enabled_draws_no_tray(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.api import sprite_media

    pack = {**sprite_media.load_pack(sprite_media.TRAY_PACK), "status": "draft"}
    monkeypatch.setattr(sprite_media, "load_pack", lambda _id: pack)
    assert sprite_media.tray_items(["bundles"]) == {}
