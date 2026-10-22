"""A flow step can carry a sprite scene; every channel shows it from the same data.

The test flow is synthetic: no product flow changes. The scene is a reference (pack, layout, item,
numbers); the web app draws it itself, the bot sends a PNG, WhatsApp shows the words.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from services.api import strings
from services.api.channels import whatsapp
from services.api.channels.base import render_step
from services.api.channels.telegram.webhook import CAPTION_MAX, HttpSender, requests_for
from services.api.flows.steps import SceneRef, Step
from services.api.sprite_media import resolve, scene_png

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
REF = SceneRef(pack="place-value-add-sub", layout="scatter", item="ball", args={"n": 23}, seed=4)


def step(ref: SceneRef | None = REF, copy: str = "sprite.tpl.add_balls") -> Step:
    return Step(kind="media", id="demo_scene", copy=copy, params={"a": 23, "b": 14}, scene=ref)


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_the_message_carries_the_reference_and_the_alt_text_in_her_language(lang: str) -> None:
    m = render_step(step(), lang)
    assert m.scene == REF.model_dump() and m.alt == strings.text(lang, "sprite.scene.scatter")
    assert "23" in m.text and "14" in m.text
    json.dumps(m.scene)  # the web adapter sends it as JSON


def test_a_step_without_a_scene_is_unchanged() -> None:
    m = render_step(step(None), "en")
    assert m.scene is None and m.alt is None


def test_the_scene_keys_exist_in_all_three_languages() -> None:
    for key in step().all_keys():
        for lang in ("en", "hi", "ta"):
            assert strings.table(lang).get(key), (lang, key)


def test_the_telegram_message_is_a_photo_with_the_words_as_the_caption() -> None:
    m = render_step(step(), "en")
    [(method, fields, files)] = requests_for(m, "42")
    assert method == "sendPhoto" and fields["caption"] == m.text and fields["chat_id"] == "42"
    name, png, mime = files["photo"]
    assert (name, mime) == ("scene.png", "image/png") and png.startswith(PNG_MAGIC)


def test_a_long_text_goes_as_the_picture_then_the_words() -> None:
    m = render_step(step(), "en")
    m.text = "x" * (CAPTION_MAX + 1)
    calls = requests_for(m, "42")
    assert [c[0] for c in calls] == ["sendPhoto", "sendMessage"]
    assert calls[0][1]["caption"] == m.alt and calls[1][1]["text"] == m.text


def test_a_scene_from_a_pack_that_is_not_enabled_is_not_drawn_and_the_words_still_go() -> None:
    m = render_step(
        step(SceneRef(pack="fractions-demo", layout="bar_model", args={"parts": [2, 3]})), "en"
    )
    [(method, fields, files)] = requests_for(m, "42")
    assert method == "sendMessage" and not files and fields["text"] == m.text


@pytest.mark.parametrize(
    "ref",
    [
        SceneRef(pack="nope", layout="row", item="ball", args={"n": 3}),
        SceneRef(pack="place-value-add-sub", layout="spiral", item="ball", args={"n": 3}),
        SceneRef(pack="place-value-add-sub", layout="row", item="chapati", args={"n": 3}),
        SceneRef(pack="place-value-add-sub", layout="row", item="ball", args={"n": 101}),
    ],
)
def test_a_reference_to_anything_the_pack_does_not_list_is_refused(ref: SceneRef) -> None:
    with pytest.raises(ValueError):
        resolve(ref)


def test_the_count_in_the_picture_is_the_count_the_flow_chose() -> None:
    assert resolve(REF).report["count_drawn"] == 23
    assert (
        resolve(
            SceneRef(
                pack="place-value-add-sub", layout="place_value_mat", item="stick", args={"n": 47}
            )
        ).report["tens"]
        == 4
    )


def test_the_png_is_small_enough_for_a_weak_connection() -> None:
    assert len(scene_png(REF)) < 60_000  # about 80 KB is the budget for a check photo


def test_whatsapp_shows_the_words_and_names_the_picture() -> None:
    text = whatsapp.to_text(render_step(step(), "hi"))
    assert strings.text("hi", "sprite.scene.scatter") in text


def test_the_http_sender_posts_a_multipart_photo(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []

    def fake_post(url: str, **kw: Any) -> None:
        sent.append({"url": url, **kw})

    monkeypatch.setattr("services.api.channels.telegram.webhook.httpx.post", fake_post)
    HttpSender("TOKEN").send("42", render_step(step(), "en"))
    assert sent[0]["url"].endswith("/sendPhoto") and sent[0]["files"]["photo"][1].startswith(
        PNG_MAGIC
    )
