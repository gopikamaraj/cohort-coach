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
    monkeypatch.delenv("STORE_SHARED", raising=False)  # separate teachers is the default
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


def test_with_STORE_SHARED_every_browser_shares_one_set_of_documents(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORE_SHARED", "1")
    client.put("/api/store/checks/x", json={"data": {"id": "x", "children": [["3", "4"]]}}, headers=h(A))
    assert client.get("/api/store", headers=h(B)).json()["checks"]["x"]["id"] == "x"  # Edge sees what Chrome wrote
    assert len(client.get("/api/store/all/checks", headers=h(A, "coach")).json()) == 1


def test_documents_written_before_sharing_join_the_shared_set(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.put("/api/store/checks/old", json={"data": {"id": "old"}}, headers=h(A))  # separate teachers: under A
    monkeypatch.setenv("STORE_SHARED", "1")
    assert client.get("/api/store", headers=h(B)).json()["checks"]["old"]["id"] == "old"


def test_a_teacher_is_her_store_key_so_the_same_nickname_on_two_browsers_shares_and_another_does_not(client: TestClient) -> None:
    key_priya, key_ravi = f"{101:016x}", f"{202:016x}"

    def on(browser: str, key: str) -> dict[str, str]:
        return {"X-Device-Id": browser, "X-Store-Key": key, "X-Role": "teacher"}

    client.put("/api/store/checks/c-1:1", json={"data": {"id": "c-1:1", "term": 1}}, headers=on(A, key_priya))
    assert client.get("/api/store", headers=on(B, key_priya)).json()["checks"]["c-1:1"]["term"] == 1  # Priya on a second browser
    assert client.get("/api/store", headers=on(B, key_ravi)).json()["checks"] == {}  # Ravi is someone else
    assert client.get("/api/store", headers=on(A, key_ravi)).json()["checks"] == {}  # even on Priya's browser
    labels = [r["teacher"] for r in client.get("/api/store/all/checks", headers=h(A, "coach")).json()]
    assert labels == ["Teacher 1"]


def test_peers_lists_other_teachers_who_show_the_same_mistake_by_nickname_and_never_a_count(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    ka, kb, kc = f"{11:016x}", f"{22:016x}", f"{33:016x}"

    def on(key: str) -> dict[str, str]:
        return {"X-Device-Id": A, "X-Store-Key": key, "X-Role": "teacher"}

    def teacher(key: str, nickname: str, class_name: str, counts: dict[str, int]) -> None:
        client.put("/api/store/settings/nickname", json={"data": {"key": "nickname", "value": nickname}}, headers=on(key))
        client.put("/api/store/classes/c-" + nickname[:2], json={"data": {"id": "c-" + nickname[:2], "name": class_name}}, headers=on(key))
        client.put("/api/store/profiles/p", json={"data": {"id": "p", "classId": "c-" + nickname[:2], "counts": counts}}, headers=on(key))

    teacher(ka, "3A Math Teacher", "3A Class", {"PV-HEARD": 4, "SUB-SFL": 0})
    teacher(kb, "3B Math Teacher", "3B Class", {"PV-HEARD": 2})
    teacher(kc, "4C Math Teacher", "4C Class", {"SUB-SFL": 5})
    seen = client.get("/api/store/peers?errors=PV-HEARD", headers=on(ka)).json()
    assert seen == [{"teacher": "3B Math Teacher", "class": "3B Class", "errors": ["PV-HEARD"]}]  # not herself, not 4C, no counts
    both = client.get("/api/store/peers?errors=PV-HEARD,SUB-SFL", headers=on(kb)).json()
    assert [p["teacher"] for p in both] == ["3A Math Teacher", "4C Math Teacher"]
    assert client.get("/api/store/peers?errors=not-a-code", headers=on(ka)).json() == []
    monkeypatch.setenv("STORE_SHARED", "1")
    assert client.get("/api/store/peers?errors=PV-HEARD", headers=on(ka)).json() == []
