"""The post-test twin of an imported pre-test: new numbers, the same skills and level, made by code."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image

from services.papers.models import PaperRow
from tests.papers_hub.test_api import Env, edit, finish, hdr, upload
from tests.papers_hub.test_api import env as env  # noqa: F401  (the fixture)


def _pre(env: Env) -> dict[str, Any]:
    v = upload(env)
    edit(env, v["id"], [{"field": "items.1.a", "value": 346}, {"field": "items.2.a", "value": 728}])
    return finish(env, v["id"])


def test_the_twin_has_the_same_shape_and_none_of_the_numbers(env: Env) -> None:  # noqa: F811
    pre = _pre(env)
    r = env.client.post(f"/api/paper-hub/papers/{pre['id']}/twin", headers=hdr("teacher"))
    assert r.status_code == 200, r.text
    twin = r.json()
    assert twin["kind"] == "post" and twin["items"] == 10
    with env.db() as db:
        a = db.get(PaperRow, pre["id"])
        b = db.get(PaperRow, twin["paper_id"] if "paper_id" in twin else twin["id"])
        assert a is not None and b is not None and b.twin_of == a.id
        assert b.findings == [] and twin["status"] == "auto_approved"
        old = [(i["operation"], i["a"], i["b"]) for i in a.body["items"]]
        new = [(i["operation"], i["a"], i["b"]) for i in b.body["items"]]
    assert [o for o, _, _ in old] == [o for o, _, _ in new]  # same questions in the same order
    assert not {(x, y) for _, x, y in old} & {(x, y) for _, x, y in new}  # no number pair repeats
    for (op, x, y), (_, p, q) in zip(old, new, strict=True):
        if op == "add":  # the same carry
            assert (x % 10 + y % 10 >= 10) == (p % 10 + q % 10 >= 10)
        if op == "subtract":  # the same borrow
            assert (x % 10 < y % 10) == (p % 10 < q % 10)
    again = env.client.post(f"/api/paper-hub/papers/{pre['id']}/twin", headers=hdr("teacher"))
    assert again.json()["id"] == twin["id"]  # asking twice gives the same twin


def test_a_post_test_that_reuses_pre_test_numbers_is_warned_about(env: Env) -> None:  # noqa: F811
    pre = _pre(env)
    other = io.BytesIO()
    Image.new("RGB", (410, 570), "white").save(
        other, "PNG"
    )  # another file, read as the same numbers
    v = upload(env, data=other.getvalue())
    out = edit(env, v["id"], [{"field": "kind", "value": "post"}])
    assert out["reuses"] and pre["check_code"] in out["reuses"]
    out = edit(env, v["id"], [{"field": "kind", "value": "pre"}])
    assert out["reuses"] == []  # only a post-test is held to this
