"""Keep an approved answer sheet for the teacher, for 60 days after she approves it.

The picture goes to a private bucket (GCS_SHEETS_BUCKET) through this API and comes back only to
the phone that stored it: it is never public and never leaves in a link. It is kept only if she
agreed (`consent=1`), it is replaced when she approves the roll number again, she can delete it at
once, and a sweep deletes it once the retention has passed, never before. Roll number only: the
sheets carry no name.
"""

from __future__ import annotations

import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.devicestore import UserDoc
from services.api.identity import user_of
from services.api.profiles import SESSION
from services.api.roles import require
from services.media.storage import BlobStore, GcsBlobStore, LocalBlobStore, StorageNotConfigured
from services.sheets_keep.models import KeptSheet

RETENTION_DAYS = int(os.environ.get("SHEET_RETENTION_DAYS", "60"))
MAX_BYTES = 800_000
CLASS = re.compile(r"^[A-Za-z0-9:_-]{1,40}$")
CHECK = re.compile(r"^[A-Za-z0-9:_-]{1,60}$")
JPEG = b"\xff\xd8\xff"

router = APIRouter(
    prefix="/api/sheet-keep",
    tags=["sheet-keep"],
    dependencies=[Depends(require("check.read_sheets"))],
)


@cache
def _store() -> BlobStore | None:
    if os.environ.get("GCS_SHEETS_BUCKET"):
        return GcsBlobStore.from_env("GCS_SHEETS")
    if os.environ.get("SHEETS_LOCAL_STORE") == "1":  # development and tests only
        secret = (os.environ.get("LINK_SECRET") or "dev-only-local-store").encode()
        return LocalBlobStore(secret, root=Path(".media-local") / "sheets")
    return None


def get_store() -> BlobStore | None:
    try:
        return _store()
    except StorageNotConfigured:
        return None


STORE = Depends(get_store)


def _now() -> datetime:
    return datetime.now(UTC)


class Owner:
    def __init__(self, class_id: str, owner: str) -> None:
        self.class_id, self.owner = class_id, owner


def owner(
    x_class_id: str | None = Header(default=None),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> Owner:
    """The signed-in user and one of her own classes (the class code, owned by her)."""
    if not x_class_id or not CLASS.match(x_class_id):
        raise HTTPException(422, "The class code is needed.")
    if db.get(UserDoc, (uid, "classes", x_class_id)) is None:
        raise HTTPException(403, "That class is not yours.")
    return Owner(x_class_id, uid)


OWNER = Depends(owner)


def _own_check(o: Owner, check_id: str) -> None:
    if not CHECK.match(check_id) or not check_id.startswith(f"{o.class_id}:"):
        raise HTTPException(403, "This is not your class's check.")


def purge_expired(db: Session, store: BlobStore | None, now: datetime | None = None) -> int:
    """Delete every sheet whose retention has passed (never one before). Returns how many."""
    when = now or _now()
    gone = 0
    for row in db.scalars(select(KeptSheet).where(KeptSheet.delete_after <= when)).all():
        if store is not None:
            try:
                store.delete(row.object_key)
            except Exception:  # noqa: BLE001 - keep the row, so the next sweep tries again
                continue
        db.delete(row)
        gone += 1
    if gone:
        db.commit()
    return gone


def _view(r: KeptSheet) -> dict[str, Any]:
    return {
        "roll": r.roll,
        "approved_at": r.approved_at.isoformat(),
        "delete_after": r.delete_after.isoformat(),
    }


def _find(db: Session, o: Owner, check_id: str, roll: int) -> KeptSheet | None:
    return db.scalars(
        select(KeptSheet).where(
            KeptSheet.class_id == o.class_id,
            KeptSheet.owner == o.owner,
            KeptSheet.check_id == check_id,
            KeptSheet.roll == roll,
        )
    ).first()


@router.get("/status")
def status(store: BlobStore | None = STORE) -> dict[str, Any]:
    return {"enabled": store is not None, "retention_days": RETENTION_DAYS}


@router.put("/{check_id}/{roll}")
def keep(
    check_id: str,
    roll: int,
    image: UploadFile = File(...),  # noqa: B008
    consent: str = Form(default=""),
    sha256: str = Form(default=""),
    o: Owner = OWNER,
    db: Session = SESSION,
    store: BlobStore | None = STORE,
) -> dict[str, Any]:
    _own_check(o, check_id)
    if consent != "1":
        raise HTTPException(403, "Sheets are kept only if you agreed to it.")
    if store is None:
        raise HTTPException(503, "Keeping sheets is not switched on here.")
    if not 1 <= roll <= 200:
        raise HTTPException(422, "The roll number is not valid.")
    data = image.file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, "That picture was empty or too large.")
    if not data.startswith(JPEG):
        raise HTTPException(422, "Only the shrunk JPEG the app makes can be kept.")
    purge_expired(db, store)
    old = _find(db, o, check_id, roll)
    key = f"sheets/{o.class_id}/{secrets.token_hex(12)}.jpg"
    try:
        store.put(key, data, "image/jpeg")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            503, "The picture could not be kept. It is still on this phone."
        ) from exc
    if old is not None:  # approved again: the new picture replaces the old one
        try:
            store.delete(old.object_key)
        except Exception:  # noqa: BLE001
            pass
        db.delete(old)
        db.flush()
    row = KeptSheet(
        id=secrets.token_hex(12),
        class_id=o.class_id,
        owner=o.owner,
        check_id=check_id,
        roll=roll,
        object_key=key,
        sha256=sha256.lower() if re.fullmatch(r"[0-9a-fA-F]{64}", sha256) else "",
        approved_at=_now(),
        delete_after=_now() + timedelta(days=RETENTION_DAYS),
    )
    db.add(row)
    db.commit()
    return _view(row)


@router.get("/{check_id}")
def listing(
    check_id: str, o: Owner = OWNER, db: Session = SESSION, store: BlobStore | None = STORE
) -> list[dict[str, Any]]:
    _own_check(o, check_id)
    purge_expired(db, store)
    rows = db.scalars(
        select(KeptSheet)
        .where(
            KeptSheet.class_id == o.class_id,
            KeptSheet.owner == o.owner,
            KeptSheet.check_id == check_id,
        )
        .order_by(KeptSheet.roll)
    ).all()
    return [_view(r) for r in rows]


def _mine(db: Session, o: Owner, check_id: str, roll: int) -> KeptSheet:
    _own_check(o, check_id)
    row = _find(db, o, check_id, roll)
    if row is None:
        raise HTTPException(404, "No kept copy of this sheet.")
    return row


@router.get("/{check_id}/{roll}/image")
def image_of(
    check_id: str,
    roll: int,
    o: Owner = OWNER,
    db: Session = SESSION,
    store: BlobStore | None = STORE,
) -> Response:
    row = _mine(db, o, check_id, roll)
    if store is None:
        raise HTTPException(503, "Keeping sheets is not switched on here.")
    try:
        data = store.get(row.object_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, "The kept copy could not be found.") from exc
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.delete("/{check_id}/{roll}")
def delete_now(
    check_id: str,
    roll: int,
    o: Owner = OWNER,
    db: Session = SESSION,
    store: BlobStore | None = STORE,
) -> dict[str, bool]:
    row = _mine(db, o, check_id, roll)
    if store is not None:
        try:
            store.delete(row.object_key)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, "The kept copy could not be deleted. Try again.") from exc
    db.delete(row)
    db.commit()
    return {"deleted": True}
