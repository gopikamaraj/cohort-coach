"""A cohort just for one class (autopilot Part D): created from her own counts, labelled by scope,
one per check, nothing about a child or another teacher, seen by a coach in counts only."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

DEV1, DEV2 = f"{1:016x}", f"{2:016x}"
BODY = {
    "check_id": "c-abc:1",
    "name": "My class: taking the smaller digit",
    "errors": ["SUB-SFL", "PV-HEARD"],
    "counts": {"SUB-SFL": 5, "PV-HEARD": 2},
    "children_checked": 16,
}


def h(role: str, device: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    if device:
        out["X-Device-Id"] = device
    return out


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def test_a_teacher_makes_a_class_only_cohort_from_her_counts(client: TestClient) -> None:
    r = client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1))
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["scope"] == "class_only" and got["classes"] == 1
    assert got["errors"] == ["SUB-SFL", "PV-HEARD"]
    assert got["counts"] == {"SUB-SFL": 5, "PV-HEARD": 2} and got["children_checked"] == 16
    mine = client.get("/api/cohorts/class-only", headers=h("teacher", DEV1)).json()
    assert [m["id"] for m in mine] == [got["id"]]


def test_a_second_tap_for_the_same_check_returns_the_same_cohort(client: TestClient) -> None:
    a = client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1)).json()
    b = client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1)).json()
    assert a["id"] == b["id"]
    assert len(client.get("/api/cohorts/class-only", headers=h("teacher", DEV1)).json()) == 1


def test_another_teacher_sees_none_of_it(client: TestClient) -> None:
    client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1))
    assert client.get("/api/cohorts/class-only", headers=h("teacher", DEV2)).json() == []


def test_the_coach_sees_it_in_counts_without_a_teacher_or_check_id(client: TestClient) -> None:
    client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1))
    r = client.get("/api/cohorts/class-only/coach", headers=h("coach"))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["scope"] == "class_only" and rows[0]["classes"] == 1
    text = json.dumps(rows)
    assert DEV1 not in text and "t-" not in text and "c-abc" not in text


def test_a_teacher_cannot_read_the_coach_list(client: TestClient) -> None:
    assert (
        client.get("/api/cohorts/class-only/coach", headers=h("teacher", DEV1)).status_code == 403
    )


def test_bad_input_is_refused(client: TestClient) -> None:
    def post(**patch: object) -> int:
        return client.post(
            "/api/cohorts/class-only", json={**BODY, **patch}, headers=h("teacher", DEV1)
        ).status_code

    assert post(errors=["NOPE"]) == 422
    assert post(errors=[]) == 422
    assert post(counts={"SUB-SFL": 99, "PV-HEARD": 2}) == 422  # more than the children checked
    assert post(counts={"SUB-SFL": 5}) == 422  # a chosen error with no count
    assert post(name="Call Ravi Kumar 9876543210") == 422  # a phone number in the name
    assert post(check_id="bad id!") == 422


def test_it_does_not_change_the_production_minimum_of_classes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.cohort_run import settings

    monkeypatch.delenv("COHORT_MIN_CLASSES", raising=False)
    client.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1))
    assert settings.production().min_classes == 15  # a class of one never lowers it
