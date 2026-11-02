# ruff: noqa: E501
"""The cloud copy of a phone's data: private to its device, readable by coaches and mentors, bounded."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session

A, B = f"{1:016x}", f"{2:016x}"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("STORE_SHARED", "0")  # the tests below are about separate phones
    engine = make_engine(f"sqlite:///{tmp_path / 's.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app)


def h(device: str, role: str = "teacher") -> dict[str, str]:
    return {"X-Device-Id": device, "X-Role": role}


def test_a_phone_reads_back_what_it_wrote_and_only_its_own(client: TestClient) -> None:
    doc = {"id": "c-1:1", "children": [["1", "2"]], "status": "closed"}
    assert client.put("/api/store/checks/c-1:1", json={"data": doc}, headers=h(A)).status_code == 200
    assert client.get("/api/store", headers=h(A)).json()["checks"] == {"c-1:1": doc}
    assert client.get("/api/store", headers=h(B)).json()["checks"] == {}  # another teacher sees nothing


def test_a_write_replaces_and_a_delete_removes(client: TestClient) -> None:
    client.put("/api/store/settings/term", json={"data": {"key": "term", "value": 1}}, headers=h(A))
    client.put("/api/store/settings/term", json={"data": {"key": "term", "value": 2}}, headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["settings"]["term"]["value"] == 2
    client.delete("/api/store/settings/term", headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["settings"] == {}
    client.put("/api/store/classes/c-1", json={"data": {"id": "c-1"}}, headers=h(A))
    client.delete("/api/store", headers=h(A))
    assert client.get("/api/store", headers=h(A)).json()["classes"] == {}


def test_coaches_and_mentors_list_every_teachers_checks_by_label_only(client: TestClient) -> None:
    check = {"id": "x", "kind": "pre", "term": 1, "status": "closed", "children": [["3", "4"], ["", ""], ["5", "6"]], "absent": [1]}
    client.put("/api/store/checks/x", json={"data": check}, headers=h(A))
    client.put("/api/store/checks/y", json={"data": {**check, "id": "y"}}, headers=h(B))
    for role in ("coach", "mentor"):
        rows = client.get("/api/store/all/checks", headers=h(A, role)).json()
        assert [r["teacher"] for r in rows] == ["Teacher 1", "Teacher 2"]
        assert A not in str(rows) and B not in str(rows)
        assert rows[0]["data"]["entered"] == 2 and rows[0]["data"]["absent"] == 1
        assert "children" not in rows[0]["data"] and "'3'" not in str(rows)  # counts only, never answers
    assert client.get("/api/store/all/checks", headers=h(A)).status_code == 403  # a teacher cannot
    assert client.get("/api/store/all/checks", headers=h(A, "officer")).status_code == 403


def test_bad_device_collection_and_size_are_refused(client: TestClient) -> None:
    assert client.get("/api/store", headers={"X-Device-Id": "nope"}).status_code == 422
    assert client.put("/api/store/transcripts/1", json={"data": {}}, headers=h(A)).status_code == 404  # rehearsals never go
    assert client.put("/api/store/checks/ok", json={"data": "x" * 300_000}, headers=h(A)).status_code == 413
    assert client.put("/api/store/checks/bad id", json={"data": {}}, headers=h(A)).status_code in (404, 422)


def test_by_default_every_browser_shares_one_set_of_documents(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STORE_SHARED", raising=False)
    client.put("/api/store/checks/x", json={"data": {"id": "x", "children": [["3", "4"]]}}, headers=h(A))
    assert client.get("/api/store", headers=h(B)).json()["checks"]["x"]["id"] == "x"  # Edge sees what Chrome wrote
    assert len(client.get("/api/store/all/checks", headers=h(A, "coach")).json()) == 1


def test_documents_written_before_sharing_join_the_shared_set(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.put("/api/store/checks/old", json={"data": {"id": "old"}}, headers=h(A))  # separate phones: under A
    monkeypatch.delenv("STORE_SHARED", raising=False)
    assert client.get("/api/store", headers=h(B)).json()["checks"]["old"]["id"] == "old"
