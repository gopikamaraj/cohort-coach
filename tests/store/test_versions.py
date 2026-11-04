# ruff: noqa: E501
"""Versions and conflicts: the later write wins, and nothing is lost silently."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

A, B = "ana", "ben"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    engine = make_engine(f"sqlite:///{tmp_path / 's.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def h(user: str) -> dict[str, str]:
    return {"X-User": user}


def put(client: TestClient, user: str, doc: dict[str, object], base: int | None = None) -> dict[str, object]:
    body: dict[str, object] = {"data": doc}
    if base is not None:
        body["base_version"] = base
    r = client.put("/api/store/checks/c1:1", json=body, headers=h(user))
    assert r.status_code == 200, r.text
    return dict(r.json())


def test_every_write_raises_the_version_by_one(client: TestClient) -> None:
    assert put(client, A, {"n": 1})["version"] == 1
    assert put(client, A, {"n": 2}, base=1)["version"] == 2
    assert client.get("/api/store/versions", headers=h(A)).json()["checks"] == {"c1:1": 2}


def test_a_write_from_the_current_version_is_no_conflict(client: TestClient) -> None:
    put(client, A, {"n": 1})
    out = put(client, A, {"n": 2}, base=1)
    assert out["conflict"] is False and client.get("/api/store/conflicts", headers=h(A)).json() == []


def test_a_write_from_an_older_version_wins_and_the_replaced_one_is_kept(client: TestClient) -> None:
    put(client, A, {"n": 1})  # v1, from the first device
    put(client, A, {"n": 2}, base=1)  # v2, the second device
    out = put(client, A, {"n": 3}, base=1)  # the first device, offline since v1
    assert out["conflict"] is True and out["version"] == 3
    assert client.get("/api/store", headers=h(A)).json()["checks"]["c1:1"] == {"n": 3}  # the later write wins
    kept = client.get("/api/store/conflicts", headers=h(A)).json()
    assert [(c["collection"], c["doc_id"], c["data"], c["overwritten_version"]) for c in kept] == [("checks", "c1:1", {"n": 2}, 2)]


def test_a_write_with_no_base_version_is_never_a_conflict(client: TestClient) -> None:
    put(client, A, {"n": 1})
    assert put(client, A, {"n": 2})["conflict"] is False


def test_conflicts_and_versions_are_private_to_their_owner(client: TestClient) -> None:
    put(client, A, {"n": 1})
    put(client, A, {"n": 2}, base=0)
    assert len(client.get("/api/store/conflicts", headers=h(A)).json()) == 1
    assert client.get("/api/store/conflicts", headers=h(B)).json() == []
    assert client.get("/api/store/versions", headers=h(B)).json()["checks"] == {}
    cid = client.get("/api/store/conflicts", headers=h(A)).json()[0]["id"]
    client.delete(f"/api/store/conflicts/{cid}", headers=h(B))  # another user cannot dismiss it
    assert len(client.get("/api/store/conflicts", headers=h(A)).json()) == 1
    client.delete(f"/api/store/conflicts/{cid}", headers=h(A))
    assert client.get("/api/store/conflicts", headers=h(A)).json() == []


def test_the_list_is_short_and_clearing_the_account_clears_it(client: TestClient) -> None:
    put(client, A, {"n": 0})
    for i in range(1, 56):
        put(client, A, {"n": i}, base=0)  # always based on the first version
    assert len(client.get("/api/store/conflicts", headers=h(A)).json()) == 50
    client.delete("/api/store", headers=h(A))
    assert client.get("/api/store/conflicts", headers=h(A)).json() == []
    assert client.get("/api/store/versions", headers=h(A)).json()["checks"] == {}
