"""My programme (cohort, mentor, lessons status) and the classroom-observation signal."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, SimObservation, make_engine
from services.api.main import app
from services.api.profiles import get_session

REAL = "c-4b7f21a9c3"
SIM = "sim-4b7f21a9c3"


@pytest.fixture
def api(tmp_path: Path) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    from services.api.devicestore import UserDoc

    with factory() as s:  # both classes belong to the default test user: a class is its owner plus its code
        for code in (REAL, SIM):
            s.add(UserDoc(owner="test user", collection="classes", doc_id=code, data={"id": code}))
        s.commit()
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def test_a_real_class_not_yet_placed_is_told_when_and_how_it_will_hear(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    body = client.get(f"/api/programme/{REAL}").json()
    assert body["placement"]["status"] == "waiting" and body["simulated"] is False
    assert body["mentor"]["status"] == "after_next_check"
    assert body["lessons"]["status"] == "not_published" and body["lessons"]["items"] == []
    assert "cohort" not in body or body["cohort"] is None


def test_a_simulated_class_sees_a_labelled_example_cohort_with_counts_only(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    body = client.get(f"/api/programme/{SIM}", params={"track": "SUB-SFL"}).json()
    assert body["simulated"] is True and body["placement"]["status"] in ("this_term", "next_term")
    assert body["placement"]["track"] == "SUB-SFL"
    cohort = body["cohort"]
    assert set(cohort) <= {"size", "undersized", "mentor_slot", "cross_block"}
    assert isinstance(cohort["size"], int) and cohort["size"] >= 1
    assert "C0" not in str(body)  # no other class or teacher is named


def test_bad_ids_and_tracks_are_refused(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    assert client.get("/api/programme/not-an-id").status_code == 422
    assert client.get(f"/api/programme/{SIM}", params={"track": "NOPE"}).status_code == 422


GOOD = {"scenario": "SUB-SFL", "language": "hi", "likeness": "some", "differences": ["quieter"]}


def test_an_observation_is_stored_as_choices_only(api) -> None:  # type: ignore[no-untyped-def]
    client, factory = api
    assert client.post("/api/practice/observations", json=GOOD).status_code == 200
    with factory() as s:
        rows = s.query(SimObservation).all()
    assert len(rows) == 1 and rows[0].likeness == "some" and rows[0].differences == ["quieter"]
    assert not hasattr(rows[0], "note") and not hasattr(rows[0], "class_id")


@pytest.mark.parametrize(
    "bad",
    [
        {**GOOD, "likeness": "very"},
        {**GOOD, "differences": ["a free text sentence"]},
        {**GOOD, "note": "Ravi said something"},
        {**GOOD, "scenario": "X"},
        {**GOOD, "differences": ["quieter"] * 20},
    ],
)
def test_free_text_and_unknown_choices_are_rejected(api, bad) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    assert client.post("/api/practice/observations", json=bad).status_code == 422


def test_the_summary_hides_small_numbers_and_shows_counts_when_there_are_enough(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    for _ in range(4):
        client.post("/api/practice/observations", json=GOOD)
    assert client.get("/api/practice/observations/summary").json()["hidden"] is True
    client.post("/api/practice/observations", json={**GOOD, "likeness": "like"})
    out = client.get("/api/practice/observations/summary").json()
    assert out["hidden"] is False and out["n"] == 5
    assert out["likeness"] == {"like": 1, "some": 4, "not_like": 0}
    assert out["differences"]["quieter"] == 5  # every one of the five report it
