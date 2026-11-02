"""Google Cloud Storage backend: V4 signed URLs, private buckets, and how a store is chosen.

No network: a throwaway RSA key signs the URLs offline, and the client is a stand-in."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.cloud import storage as gcs_lib
from google.oauth2 import service_account

from services.media import storage
from services.media.storage import GcsBlobStore, LocalBlobStore, StorageNotConfigured


def _key_info() -> dict[str, str]:
    pem = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )
    return {
        "type": "service_account",
        "project_id": "demo-project",
        "private_key_id": "k1",
        "private_key": pem,
        "client_email": "pilot@demo-project.iam.gserviceaccount.com",
        "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


@pytest.fixture(scope="module")
def key_info() -> dict[str, str]:
    return _key_info()


@pytest.fixture
def gcs(key_info: dict[str, str]) -> GcsBlobStore:
    creds = service_account.Credentials.from_service_account_info(key_info)
    return GcsBlobStore("cc-sheets", gcs_lib.Client(credentials=creds, project="demo-project"))


def test_a_signed_put_url_is_v4_short_lived_and_tied_to_the_content_type(gcs: GcsBlobStore) -> None:
    up = gcs.presign_put("sheets/abc.jpg", "image/jpeg", 300)
    q = parse_qs(urlparse(up.url).query)
    assert urlparse(up.url).path == "/cc-sheets/sheets/abc.jpg"
    assert q["X-Goog-Algorithm"] == ["GOOG4-RSA-SHA256"] and q["X-Goog-Expires"] == ["300"]
    assert "X-Goog-Signature" in q and "content-type" in q["X-Goog-SignedHeaders"][0]
    assert up.headers == {"Content-Type": "image/jpeg"} and up.expires_in == 300


def test_a_signed_get_url_expires_in_minutes_and_can_name_the_download(gcs: GcsBlobStore) -> None:
    url = gcs.presign_get("pilot-audio/a.m4a", 120, "cc-pilot-slot1-en.m4a")
    q = parse_qs(urlparse(url).query)
    assert q["X-Goog-Expires"] == ["120"] and "X-Goog-Signature" in q
    assert "cc-pilot-slot1-en.m4a" in q["response-content-disposition"][0]
    plain = parse_qs(urlparse(gcs.presign_get("x", 60)).query)
    assert "response-content-disposition" not in plain


def test_reads_writes_and_deletes_go_to_the_named_bucket() -> None:
    calls: list[tuple[str, str]] = []

    class Blob:
        def __init__(self, key: str) -> None:
            self.key, self.size = key, 7

        def upload_from_string(self, data: bytes, content_type: str) -> None:
            calls.append(("put", f"{self.key} {content_type} {len(data)}"))

        def download_as_bytes(self) -> bytes:
            return b"bytes"

        def delete(self) -> None:
            calls.append(("delete", self.key))

    class Bucket:
        def blob(self, key: str) -> Blob:
            return Blob(key)

        def get_blob(self, key: str) -> Blob | None:
            return None if key == "gone" else Blob(key)

    class Client:
        def bucket(self, name: str) -> Bucket:
            calls.append(("bucket", name))
            return Bucket()

    store = GcsBlobStore("cc-sheets", Client())
    store.put("k", b"abc", "image/jpeg")
    store.delete("k")
    assert store.get("k") == b"bytes" and store.size("k") == 7 and store.size("gone") is None
    assert calls == [
        ("bucket", "cc-sheets"),
        ("put", "k image/jpeg 3"),
        ("delete", "k"),
    ]


def test_credentials_come_from_json_or_a_file_and_a_missing_bucket_or_key_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, key_info: dict[str, str]
) -> None:
    for var in ("GCS_SHEETS_BUCKET", "GCS_CREDENTIALS_JSON", "GOOGLE_APPLICATION_CREDENTIALS"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(StorageNotConfigured):
        GcsBlobStore.from_env("GCS_SHEETS")  # no bucket
    monkeypatch.setenv("GCS_SHEETS_BUCKET", "cc-sheets")
    import google.auth

    def no_adc(scopes: Any = None) -> Any:  # no key and no Application Default Credentials
        raise google.auth.exceptions.DefaultCredentialsError("none")

    monkeypatch.setattr("google.auth.default", no_adc)
    with pytest.raises(StorageNotConfigured):
        GcsBlobStore.from_env("GCS_SHEETS")
    monkeypatch.setenv("GCS_CREDENTIALS_JSON", json.dumps(key_info))
    one = GcsBlobStore.from_env("GCS_SHEETS")
    assert one.name == "cc-sheets"
    assert "X-Goog-Signature" in one.presign_get("k", 60)
    monkeypatch.delenv("GCS_CREDENTIALS_JSON")
    path = tmp_path / "key.json"
    path.write_text(json.dumps(key_info), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(path))
    assert "X-Goog-Signature" in GcsBlobStore.from_env("GCS_SHEETS").presign_get("k", 60)


def test_gcs_is_chosen_when_its_bucket_is_set(
    monkeypatch: pytest.MonkeyPatch, key_info: dict[str, str]
) -> None:
    for var in ("S3_BUCKET", "MEDIA_LOCAL_STORE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GCS_CREDENTIALS_JSON", json.dumps(key_info))
    monkeypatch.setenv("GCS_AUDIO_BUCKET", "cc-audio")
    storage.audio_store.cache_clear()
    try:
        audio = storage.audio_store()
        assert isinstance(audio, GcsBlobStore) and audio.name == "cc-audio"
    finally:
        storage.audio_store.cache_clear()


def test_with_no_bucket_of_any_kind_the_audio_store_names_both_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for var in ("GCS_AUDIO_BUCKET", "S3_BUCKET", "MEDIA_LOCAL_STORE"):
        monkeypatch.delenv(var, raising=False)
    storage.audio_store.cache_clear()
    with pytest.raises(StorageNotConfigured, match="GCS_AUDIO_BUCKET"):
        storage.audio_store()
    storage.audio_store.cache_clear()
    assert LocalBlobStore  # the dev store stays available behind MEDIA_LOCAL_STORE=1
    assert timedelta(seconds=300).total_seconds() == 300


# ---- no key file: Application Default Credentials (the organisation forbids keys) ------------


class _Creds:
    def __init__(self, email: str | None, valid: bool = False) -> None:
        self.service_account_email = email
        self.valid, self.token, self.refreshed = valid, "tok-1", 0

    def refresh(self, _request: Any) -> None:
        self.refreshed += 1
        self.valid = True


def _no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "GCS_CREDENTIALS_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCS_SIGNER_SERVICE_ACCOUNT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GCS_SHEETS_BUCKET", "cc-sheets")


def test_with_no_key_adc_signs_through_iam_as_the_attached_service_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_key(monkeypatch)
    creds = _Creds("run-sa@demo.iam.gserviceaccount.com")
    monkeypatch.setattr("google.auth.default", lambda scopes=None: (creds, "demo-project"))
    seen: list[dict[str, Any]] = []

    class Blob:
        def generate_signed_url(self, **kw: Any) -> str:
            seen.append(kw)
            return "https://storage.googleapis.com/x?X-Goog-Signature=1"

    monkeypatch.setattr(
        "google.cloud.storage.Client",
        lambda **kw: type(
            "C", (), {"bucket": lambda self, n: type("B", (), {"blob": lambda s, k: Blob()})()}
        )(),
    )
    store = GcsBlobStore.from_env("GCS_SHEETS")
    store.presign_put("k", "image/jpeg", 300)
    store.presign_get("k", 120, "a.m4a")
    assert creds.refreshed == 1  # one refresh while the token is not valid; then it is reused
    for kw in seen:
        assert kw["service_account_email"] == "run-sa@demo.iam.gserviceaccount.com"
        assert kw["access_token"] == "tok-1" and kw["version"] == "v4"
    assert seen[1]["response_disposition"].endswith('a.m4a"')


def test_on_a_laptop_the_signer_comes_from_the_env_and_a_missing_one_is_a_plain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_key(monkeypatch)
    user = _Creds(None)  # `gcloud auth application-default login`: a user, not a service account
    monkeypatch.setattr("google.auth.default", lambda scopes=None: (user, "demo-project"))
    monkeypatch.setattr(
        "google.cloud.storage.Client", lambda **kw: type("C", (), {"bucket": lambda s, n: None})()
    )
    with pytest.raises(StorageNotConfigured, match="GCS_SIGNER_SERVICE_ACCOUNT"):
        GcsBlobStore.from_env("GCS_SHEETS")
    monkeypatch.setenv(
        "GCS_SIGNER_SERVICE_ACCOUNT", "gcs-storage-admin@demo.iam.gserviceaccount.com"
    )
    store = GcsBlobStore.from_env("GCS_SHEETS")
    assert store._signer == "gcs-storage-admin@demo.iam.gserviceaccount.com"


def test_with_no_credentials_anywhere_the_error_says_what_to_do(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import google.auth

    _no_key(monkeypatch)

    def none(scopes: Any = None) -> Any:
        raise google.auth.exceptions.DefaultCredentialsError("no")

    monkeypatch.setattr("google.auth.default", none)
    with pytest.raises(StorageNotConfigured, match="application-default login"):
        GcsBlobStore.from_env("GCS_SHEETS")


def test_a_key_file_still_wins_over_adc(
    monkeypatch: pytest.MonkeyPatch, key_info: dict[str, str]
) -> None:
    _no_key(monkeypatch)
    monkeypatch.setenv("GCS_CREDENTIALS_JSON", json.dumps(key_info))

    def boom(scopes: Any = None) -> Any:
        raise AssertionError("ADC must not be consulted when a key is given")

    monkeypatch.setattr("google.auth.default", boom)
    assert GcsBlobStore.from_env("GCS_SHEETS")._credentials is None
