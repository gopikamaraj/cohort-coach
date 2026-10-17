from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, ProfileSync, make_engine
from services.api.main import app
from services.api.profiles import get_session

GOOD: dict[str, Any] = {
    "term": "T1",
    "form": "A",
    "children_checked": 28,
    "counts": {"PV-HEARD": 2, "PV-REVERSE": 0, "ADD-NOCARRY": 5, "SUB-SFL": 11, "SUB-NODEC": 3},
    "anchor_wrong_count": 1,
    "untracked": {"ADD-WHOLE-ONES": 2},
    "simulated": True,
}
URL = "/api/classes/c-4b7f21/profile"


@pytest.fixture
def api(tmp_path: Path) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def test_a_counts_only_profile_is_stored_and_replaced(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    c, factory = api
    res = c.post(URL, json=GOOD)
    assert res.status_code == 200 and res.json()["stored"] is True
    again = {**GOOD, "counts": {**GOOD["counts"], "SUB-SFL": 12}}
    assert c.post(URL, json=again).status_code == 200
    with factory() as s:
        rows = s.query(ProfileSync).all()
    assert len(rows) == 1 and rows[0].counts["SUB-SFL"] == 12 and rows[0].simulated is True


@pytest.mark.parametrize(
    "extra",
    [
        {"children": [["346", "728"]]},  # a per-child array
        {"answers": [[1, 2, 3]]},
        {"roll_numbers": [1, 2, 3]},
        {"roll": 7},
        {"child_names": ["Ravi"]},
        {"teacher": "A. Kumar"},
        {"photo": "data:image/jpeg;base64,AAAA"},
    ],
)
def test_any_per_child_or_identifying_field_is_rejected(
    api: tuple[TestClient, sessionmaker[Session]], extra: dict[str, Any]
) -> None:
    c, factory = api
    assert c.post(URL, json={**GOOD, **extra}).status_code == 422
    with factory() as s:
        assert s.query(ProfileSync).count() == 0  # nothing was stored


def test_a_count_must_be_a_known_error_within_the_class_size(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    c, _ = api
    bad_bodies = [
        {**GOOD, "counts": {**GOOD["counts"], "SUB-SFL": 29}},  # more than children checked
        {**GOOD, "counts": {"RANDOM": 1}},
        {**GOOD, "counts": {"SUB-SFL": [1, 2]}},  # an array instead of a count
        {**GOOD, "counts": {"SUB-SFL": -1}},
        {**GOOD, "untracked": {"Ravi": 1}},
        {**GOOD, "form": "C"},
        {**GOOD, "term": "next"},
    ]
    for bad in bad_bodies:
        assert c.post(URL, json=bad).status_code == 422


def test_the_class_id_cannot_carry_a_name_or_roll_number(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    c, _ = api
    assert c.post("/api/classes/Ravi Kumar roll 7/profile", json=GOOD).status_code in (404, 422)
    assert c.post("/api/classes/a/profile", json=GOOD).status_code == 422


def test_the_demo_block_is_simulated_and_has_no_child_level_data(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    c, _ = api
    body = c.get("/api/demo/block").json()
    assert body["simulated"] is True and body["classes"] == 120
    assert set(body["terms"]) == {"T1", "T2"}
    t1 = body["terms"]["T1"]
    assert t1["children_showing"]["SUB-SFL"] <= t1["children_checked"]
    assert "roll" not in str(body).lower() and "children" not in body
