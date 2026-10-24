"""Page 1, Upload sheets: the consent gate, signed URLs, duplicates, retries, reading, retention."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from services.api.db import PilotAudit, PilotClassCount, PilotSheet
from services.pilot.storage import S3BlobStore, StorageNotConfigured
from tests.pilot.conftest import Env, answers, init_body, photo, upload

URL_RE = re.compile(r"https?://|/api/pilot/blob/")


def test_the_consent_gate_blocks_an_upload(env: Env) -> None:
    data = photo(1)
    for over in (
        {"consent_confirmed": False},
        {"consent_ref": ""},
        {"consent_ref": "  "},
        {"consent_ref": "!!"},
    ):
        res = env.client.post(
            "/api/pilot/sheets/init", json=init_body(data, **over), headers=env.h("ops")
        )
        assert res.status_code == 403, over
    with env.factory() as db:
        assert db.execute(select(PilotSheet)).first() is None  # nothing was even started


def test_the_consent_reference_is_stored_with_each_sheet(env: Env) -> None:
    upload(env, photo(1), read=answers(False))
    with env.factory() as db:
        sheet = db.execute(select(PilotSheet)).scalar_one()
        assert sheet.consent_ref == "HM-LETTER-2026-10"
        assert sheet.test_phase == "pre" and sheet.uploaded_by == "ops"


def test_the_sheet_goes_to_the_private_bucket_by_a_signed_url_and_is_read(env: Env) -> None:
    out = upload(env, photo(1), read=answers(False))
    assert out["status"] == "read"
    assert len(env.sheets.keys()) == 1 and env.audio.keys() == []  # never the audio bucket
    assert env.client.get("/api/pilot/sheets/summary", headers=env.h()).json()["read"] == 1


def test_a_duplicate_checksum_is_skipped(env: Env) -> None:
    first = upload(env, photo(1), read=answers(False))
    again = upload(env, photo(1))
    assert again["duplicate"] is True and again["id"] == first["id"]
    assert len(env.sheets.keys()) == 1
    # the same photo for another school is a different sheet
    other = upload(env, photo(1), read=answers(False), school_code="SCH-02")
    assert other["duplicate"] is False


def test_a_failed_file_can_be_retried(env: Env) -> None:
    data = photo(1)
    res = env.client.post("/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops"))
    sheet_id = res.json()["id"]
    # the phone lost signal before the PUT: completing finds no file
    done = env.client.post(f"/api/pilot/sheets/{sheet_id}/complete", headers=env.h("ops"))
    assert done.status_code == 409
    with env.factory() as db:
        assert db.get(PilotSheet, sheet_id).status == "failed"  # type: ignore[union-attr]
    # retry: the same checksum gets a fresh URL on the same sheet, and this time it works
    env.models.queue(answers(False))
    retry = env.client.post("/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops"))
    assert retry.json()["id"] == sheet_id and retry.json()["duplicate"] is False
    up = retry.json()["upload"]
    assert env.client.put(up["url"], content=data, headers=up["headers"]).status_code == 200
    assert env.client.post(f"/api/pilot/sheets/{sheet_id}/complete", headers=env.h("ops")).json()[
        "status"
    ] in (
        "stored",
        "read",
    )


def test_a_short_upload_is_not_marked_stored(env: Env) -> None:
    data = photo(1)
    res = env.client.post("/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops"))
    up = res.json()["upload"]
    env.client.put(up["url"], content=data[:-5], headers=up["headers"])
    assert (
        env.client.post(
            f"/api/pilot/sheets/{res.json()['id']}/complete", headers=env.h("ops")
        ).status_code
        == 409
    )


def test_a_short_or_oversized_object_is_deleted_not_kept(env: Env) -> None:
    data = photo(1)
    res = env.client.post(
        "/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops")
    ).json()
    up = res["upload"]
    env.client.put(
        up["url"], content=data + b"extra", headers=up["headers"]
    )  # larger than declared
    assert env.sheets.keys() != []
    done = env.client.post(f"/api/pilot/sheets/{res['id']}/complete", headers=env.h("ops"))
    assert done.status_code == 409 and env.sheets.keys() == []


def test_the_local_store_refuses_a_huge_upload(env: Env) -> None:
    data = photo(1)
    res = env.client.post(
        "/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops")
    ).json()
    big = b"x" * 8_000_001
    put = env.client.put(res["upload"]["url"], content=big, headers=res["upload"]["headers"])
    assert put.status_code == 413


def test_no_public_url_exists_for_any_sheet(env: Env) -> None:
    seen: list[str] = []
    upload(env, photo(1), read=answers(False))
    key = env.sheets.keys()[0]
    for path in ("/api/pilot/sheets", "/api/pilot/sheets/summary", "/api/pilot/config"):
        seen.append(env.client.get(path, headers=env.h()).text)
    seen.append(
        json.dumps(
            env.client.post(
                "/api/pilot/sheets/init", json=init_body(photo(1)), headers=env.h("ops")
            ).json()
        )
    )
    for text in seen:
        assert (
            key not in text and "sheets/" not in text
        )  # no key, no bucket path, no URL in any list
        assert not URL_RE.search(text)
    # the object cannot be fetched by its key, with no token, or with a token from the audio bucket
    assert env.client.get(f"/api/pilot/blob/{key}").status_code in (403, 404)
    assert env.client.get(f"/api/pilot/blob/sheets/{key}").status_code in (403, 404)
    sheet_id = key.split("/")[1].split(".")[0]
    # the only way to a photo is a signed link, for a role that may have one
    assert (
        env.client.get(f"/api/pilot/sheets/{sheet_id}/url", headers=env.h("rev")).status_code == 403
    )
    assert (
        env.client.get(f"/api/pilot/sheets/{sheet_id}/url", headers=env.h("off")).status_code == 403
    )
    assert env.client.get(f"/api/pilot/sheets/{sheet_id}/url").status_code == 401
    link = env.client.get(f"/api/pilot/sheets/{sheet_id}/url", headers=env.h("ops")).json()
    assert env.client.get(link["url"]).status_code == 200


def test_signed_urls_expire(env: Env) -> None:
    data = photo(1)
    res = env.client.post(
        "/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops")
    ).json()
    env.clock.now += res["upload"]["expires_in"] + 1
    late = env.client.put(res["upload"]["url"], content=data, headers=res["upload"]["headers"])
    assert late.status_code == 403
    upload(env, photo(2), read=answers(False))
    sheet_id = env.sheets.keys()[0].split("/")[1].split(".")[0]
    link = env.client.get(f"/api/pilot/sheets/{sheet_id}/url", headers=env.h("ops")).json()
    assert env.client.get(link["url"]).status_code == 200
    env.clock.now += link["expires_in"] + 1
    assert env.client.get(link["url"]).status_code == 403


def test_a_signed_s3_url_is_signed_short_lived_and_asks_for_encryption() -> None:
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url="https://s3.example.test",
        region_name="ap-south-1",
        aws_access_key_id="AKIATEST",
        aws_secret_access_key="secret",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    store = S3BlobStore("cc-sheets", client)
    put = store.presign_put("sheets/abc.jpg", "image/jpeg", 300)
    assert "X-Amz-Signature=" in put.url and "X-Amz-Expires=300" in put.url
    assert "x-amz-server-side-encryption" in put.url.lower()  # the encryption header is signed
    assert put.headers["x-amz-server-side-encryption"] == "AES256"
    get = store.presign_get("sheets/abc.jpg", 120)
    assert "X-Amz-Signature=" in get and "X-Amz-Expires=120" in get
    assert "cc-sheets/sheets/abc.jpg?" in get  # a signed query is always present


def test_the_sheets_bucket_must_not_be_the_audio_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.pilot import storage

    storage.sheets_store.cache_clear()
    monkeypatch.setenv("S3_BUCKET", "same")
    monkeypatch.setenv("S3_SHEETS_BUCKET", "same")
    with pytest.raises(StorageNotConfigured):
        storage.sheets_store()
    storage.sheets_store.cache_clear()
    monkeypatch.delenv("S3_SHEETS_BUCKET")
    monkeypatch.delenv("PILOT_LOCAL_STORE", raising=False)
    with pytest.raises(StorageNotConfigured):  # no silent local fallback for children's sheets
        storage.sheets_store()
    storage.sheets_store.cache_clear()


def test_no_child_name_column_or_name_field_exists(env: Env) -> None:
    cols = {c.name for c in PilotSheet.__table__.columns}
    assert cols == {
        "id", "school_code", "class_code", "teacher_ref", "test_phase", "object_key", "sha256",
        "bytes", "mime", "consent_ref", "uploaded_by", "uploaded_at", "status", "note",
    }  # fmt: skip
    for table in (PilotSheet.__table__, PilotClassCount.__table__):
        assert not [
            c.name for c in table.columns if re.search(r"name|pupil|student|roll|^child_", c.name)
        ]
    # the API refuses a free-text name field outright
    res = env.client.post(
        "/api/pilot/sheets/init",
        json={**init_body(photo(1)), "child_name": "Meena"},
        headers=env.h("ops"),
    )
    assert res.status_code == 422
    # and a code that looks like a name or a sentence
    for field, value in (
        ("school_code", "Government Primary School"),
        ("teacher_ref", "Mrs Lakshmi"),
        ("class_code", "3 A section"),
    ):
        res = env.client.post(
            "/api/pilot/sheets/init",
            json=init_body(photo(1), **{field: value}),
            headers=env.h("ops"),
        )
        assert res.status_code == 422, field


def test_a_sheet_the_reader_is_unsure_of_needs_a_second_look_and_adds_no_counts(env: Env) -> None:
    out = upload(env, photo(1), read=answers(True))
    assert out["status"] == "read"
    env.models.confidence = 0.4  # now the reader is unsure of every box
    out = upload(env, photo(2), read=answers(True))
    summary = env.client.get("/api/pilot/sheets/summary", headers=env.h()).json()
    assert (summary["uploaded"], summary["read"], summary["needs_look"]) == (2, 1, 1)
    with env.factory() as db:
        assert db.execute(select(PilotClassCount)).scalar_one().children_checked == 1


def test_heic_and_pdf_are_stored_and_wait_for_a_second_look(env: Env) -> None:
    upload(env, photo(1), mime="image/heic")
    upload(env, photo(2), mime="application/pdf")
    summary = env.client.get("/api/pilot/sheets/summary", headers=env.h()).json()
    assert (summary["uploaded"], summary["read"], summary["needs_look"]) == (2, 0, 2)
    assert env.models.reads == 0  # call 8 was not asked to read a format it cannot take


def test_only_class_level_counts_are_kept_from_a_read(env: Env) -> None:
    upload(env, photo(1), read=answers(True))
    upload(env, photo(2), read=answers(False))
    with env.factory() as db:
        row = db.execute(select(PilotClassCount)).scalar_one()
        assert row.children_checked == 2 and row.counts == {"SUB-SFL": 1}
        dump = json.dumps([c.name for c in PilotClassCount.__table__.columns])
        assert "answer" not in dump and "reads" not in dump


# ---- retention and deletion -----------------------------------------------------------------


def test_retention_deletes_old_photos_and_is_audit_logged(env: Env) -> None:
    upload(env, photo(1), read=answers(False))
    with env.factory() as db:
        sheet = db.execute(select(PilotSheet)).scalar_one()
        sheet.uploaded_at = datetime.now(UTC) - timedelta(days=100)
        db.commit()
    res = env.client.put(
        "/api/pilot/config/retention", json={"retention_days": 30}, headers=env.h("ops")
    )
    assert res.status_code == 200
    ran = env.client.post("/api/pilot/sheets/retention/run", headers=env.h("ops")).json()
    assert ran["deleted"] == 1 and env.sheets.keys() == []
    with env.factory() as db:
        assert db.execute(select(PilotSheet)).first() is None
        actions = [a.action for a in db.execute(select(PilotAudit)).scalars()]
        assert "config.retention" in actions and "sheets.retention" in actions


def test_the_retention_period_is_validated(env: Env) -> None:
    for days in (0, 6, 366):
        res = env.client.put(
            "/api/pilot/config/retention", json={"retention_days": days}, headers=env.h("ops")
        )
        assert res.status_code == 422
    assert (
        env.client.put(
            "/api/pilot/config/retention", json={"retention_days": 30}, headers=env.h("rev")
        ).status_code
        == 403
    )


def test_delete_all_for_a_school_removes_photos_rows_and_counts_and_is_logged(env: Env) -> None:
    upload(env, photo(1), read=answers(True))
    upload(env, photo(2), read=answers(True))
    upload(env, photo(3), read=answers(True), school_code="SCH-02")
    url = "/api/pilot/sheets/school/SCH-01"
    assert env.client.delete(url, headers=env.h("ops")).status_code == 422  # must type the code
    assert env.client.delete(url + "?confirm=SCH-01", headers=env.h("rev")).status_code == 403
    out = env.client.delete(url + "?confirm=SCH-01", headers=env.h("ops")).json()
    assert out == {"sheets": 2, "classes": 1}
    assert len(env.sheets.keys()) == 1  # the other school's photo is untouched
    with env.factory() as db:
        assert {s.school_code for s in db.execute(select(PilotSheet)).scalars()} == {"SCH-02"}
        assert {c.school_code for c in db.execute(select(PilotClassCount)).scalars()} == {"SCH-02"}
        row = db.execute(
            select(PilotAudit).where(PilotAudit.action == "sheets.delete_school")
        ).scalar_one()
        assert row.detail == {"sheets": 2, "classes": 1} and row.target == "SCH-01"
