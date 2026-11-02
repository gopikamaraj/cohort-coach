"""Kept answer sheets: only with consent, only for their owner, replaced on re-approval, deleted
by the teacher at once, and by the sweep 60 days after approval, never before."""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.media.storage import LocalBlobStore
from services.sheets_keep import api as keep
from services.sheets_keep.models import KeptSheet

CHECK = "c-own1:1"


def jpeg(color: int = 200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 56), (color, color, color)).save(buf, "JPEG")
    return buf.getvalue()


class Env:
    def __init__(self, client: TestClient, store: LocalBlobStore, factory: sessionmaker[Session]):
        self.client, self.store, self.factory = client, store, factory

    def put(
        self,
        roll: int = 3,
        *,
        consent: str = "1",
        device: str = "device-aaaa1",
        cls: str = "c-own1",
        check: str = CHECK,
        data: bytes | None = None,
    ):  # type: ignore[no-untyped-def]
        return self.client.put(
            f"/api/sheet-keep/{check}/{roll}",
            files={"image": ("s.jpg", data or jpeg(), "image/jpeg")},
            data={"consent": consent},
            headers={"X-Role": "teacher", "X-Class-Id": cls, "X-Device-Id": device},
        )

    def hdr(self, device: str = "device-aaaa1", cls: str = "c-own1") -> dict[str, str]:
        return {"X-Role": "teacher", "X-Class-Id": cls, "X-Device-Id": device}


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    engine = make_engine(f"sqlite:///{tmp_path / 'keep.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    store = LocalBlobStore(b"test-secret", root=tmp_path / "bucket")
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[keep.get_store] = lambda: store
    yield Env(TestClient(app), store, factory)


def test_a_sheet_is_kept_only_if_she_agreed(env: Env) -> None:
    assert env.put(consent="").status_code == 403
    assert env.put(consent="0").status_code == 403
    assert env.store.keys() == []  # nothing was stored
    ok = env.put()
    assert ok.status_code == 200 and ok.json()["roll"] == 3
    assert len(env.store.keys()) == 1


def test_the_retention_is_sixty_days_from_approval(env: Env) -> None:
    assert keep.RETENTION_DAYS == 60
    body = env.put().json()
    kept = datetime.fromisoformat(body["delete_after"]) - datetime.fromisoformat(
        body["approved_at"]
    )
    assert kept == timedelta(days=60)


def test_only_the_owner_can_list_read_or_delete_it(env: Env) -> None:
    env.put()
    other = env.hdr(device="device-bbbb2")
    assert env.client.get(f"/api/sheet-keep/{CHECK}", headers=other).json() == []
    assert env.client.get(f"/api/sheet-keep/{CHECK}/3/image", headers=other).status_code == 404
    assert env.client.delete(f"/api/sheet-keep/{CHECK}/3", headers=other).status_code == 404
    other_class = env.hdr(cls="c-other")
    assert env.client.get(f"/api/sheet-keep/{CHECK}", headers=other_class).status_code == 403
    mine = env.client.get(f"/api/sheet-keep/{CHECK}/3/image", headers=env.hdr())
    assert mine.status_code == 200 and mine.headers["content-type"] == "image/jpeg"
    assert mine.headers["cache-control"] == "no-store" and mine.content == jpeg()
    assert [
        r["roll"] for r in env.client.get(f"/api/sheet-keep/{CHECK}", headers=env.hdr()).json()
    ] == [3]


def test_approving_again_replaces_the_picture_and_leaves_one_copy(env: Env) -> None:
    env.put(data=jpeg(100))
    env.put(data=jpeg(220))
    assert len(env.store.keys()) == 1
    got = env.client.get(f"/api/sheet-keep/{CHECK}/3/image", headers=env.hdr()).content
    assert got == jpeg(220)


def test_she_can_delete_it_at_once(env: Env) -> None:
    env.put()
    assert env.client.delete(f"/api/sheet-keep/{CHECK}/3", headers=env.hdr()).json() == {
        "deleted": True
    }
    assert env.store.keys() == []
    assert env.client.get(f"/api/sheet-keep/{CHECK}/3/image", headers=env.hdr()).status_code == 404


def test_nothing_is_deleted_before_sixty_days_and_everything_after(env: Env) -> None:
    env.put(3)
    env.put(4)
    now = datetime.now(UTC)
    with env.factory() as db:
        assert keep.purge_expired(db, env.store, now + timedelta(days=59, hours=23)) == 0
        assert len(env.store.keys()) == 2
        assert keep.purge_expired(db, env.store, now + timedelta(days=60, minutes=1)) == 2
        assert env.store.keys() == [] and db.query(KeptSheet).count() == 0


def test_bad_pictures_and_other_classes_checks_are_refused(env: Env) -> None:
    assert env.put(data=b"\x89PNG not a jpeg").status_code == 422
    assert env.put(data=b"\xff\xd8\xff" + b"0" * 900_000).status_code == 413
    assert env.put(roll=0).status_code == 422
    assert env.put(check="c-other:1").status_code == 403


def test_without_a_bucket_it_says_so_and_keeps_nothing(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[keep.get_store] = lambda: None
    c = TestClient(app)
    h = {"X-Role": "teacher", "X-Class-Id": "c-own1", "X-Device-Id": "device-aaaa1"}
    assert c.get("/api/sheet-keep/status", headers=h).json() == {
        "enabled": False,
        "retention_days": 60,
    }
