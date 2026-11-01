"""Object storage for published audio: a bucket, short-lived signed URLs, no public URL.

`S3BlobStore` talks to any S3-compatible service and `GcsBlobStore` to Google Cloud Storage.
`LocalBlobStore` is for tests and for local development only (MEDIA_LOCAL_STORE=1): it signs its
URLs the same way, so expiry is testable. No store ever returns a bucket URL that works without a
signature. Answer-sheet photos are never stored: there is no sheets bucket.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from functools import cache
from pathlib import Path
from typing import Any, Protocol

SSE = "AES256"


@dataclass(frozen=True)
class SignedUpload:
    url: str
    headers: dict[str, str]
    expires_in: int


class BlobStore(Protocol):
    def presign_put(self, key: str, content_type: str, expires: int = 300) -> SignedUpload: ...
    def presign_get(self, key: str, expires: int = 120, filename: str | None = None) -> str: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def size(self, key: str) -> int | None: ...
    def delete(self, key: str) -> None: ...


class StorageNotConfigured(RuntimeError):
    pass


class S3BlobStore:
    """S3-compatible bucket. Server-side encryption is requested on every write; the signed upload
    URL binds the encryption header, so the browser must send it."""

    def __init__(self, bucket: str, client: Any) -> None:
        self.bucket = bucket
        self.client = client

    @classmethod
    def from_env(cls, prefix: str) -> S3BlobStore:
        import boto3
        from botocore.config import Config

        bucket = os.environ.get(f"{prefix}_BUCKET", "")
        if not bucket:
            raise StorageNotConfigured(f"{prefix}_BUCKET is not set")
        client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("S3_ENDPOINT") or None,
            region_name=os.environ.get(f"{prefix}_REGION") or os.environ.get("S3_REGION") or None,
            aws_access_key_id=os.environ.get(f"{prefix}_ACCESS_KEY_ID")
            or os.environ.get("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get(f"{prefix}_SECRET_ACCESS_KEY")
            or os.environ.get("S3_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        return cls(bucket, client)

    def presign_put(self, key: str, content_type: str, expires: int = 300) -> SignedUpload:
        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
                "ServerSideEncryption": SSE,
            },
            ExpiresIn=expires,
        )
        return SignedUpload(
            url, {"Content-Type": content_type, "x-amz-server-side-encryption": SSE}, expires
        )

    def presign_get(self, key: str, expires: int = 120, filename: str | None = None) -> str:
        params: dict[str, Any] = {"Bucket": self.bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return str(
            self.client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires)
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption=SSE,
        )

    def get(self, key: str) -> bytes:
        return bytes(self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read())

    def size(self, key: str) -> int | None:
        try:
            return int(self.client.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except Exception:  # missing key or no access: the object is not there for our purposes
            return None

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


class GcsBlobStore:
    """Google Cloud Storage (a Firebase Storage bucket is a GCS bucket, so this covers both).

    Signed URLs are V4 and short-lived. GCS encrypts every object at rest by default, so no
    encryption header is needed. Keep the bucket private: uniform bucket-level access on and
    "public access prevention" enforced.

    Three ways to authenticate (`from_env`), in this order:
      1. a service-account key (GCS_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS): URLs are
         signed locally with its private key;
      2. no key, because the organisation forbids creating one: Application Default Credentials.
         On Cloud Run, Compute Engine and the like that is the attached service account, read from
         the metadata server; on a laptop it is `gcloud auth application-default login`;
      3. in case 2 URLs cannot be signed locally, so they are signed by the IAM Credentials API on
         behalf of a service account (`signer`): the attached one on GCP, or
         GCS_SIGNER_SERVICE_ACCOUNT
         on a laptop. The caller needs "Service Account Token Creator" on that account.
    """

    def __init__(
        self, bucket: str, client: Any, *, credentials: Any = None, signer: str | None = None
    ) -> None:
        self.name = bucket
        self.bucket = client.bucket(bucket)
        self._credentials = credentials  # set only when URLs are signed through IAM (no key)
        self._signer = signer

    @classmethod
    def from_env(cls, prefix: str) -> GcsBlobStore:
        """`prefix` is GCS_SHEETS or GCS_AUDIO."""
        import google.auth
        from google.cloud import storage
        from google.oauth2 import service_account

        bucket = os.environ.get(f"{prefix}_BUCKET", "")
        if not bucket:
            raise StorageNotConfigured(f"{prefix}_BUCKET is not set")
        raw = os.environ.get("GCS_CREDENTIALS_JSON", "").strip()
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if raw or path:
            creds = (
                service_account.Credentials.from_service_account_info(json.loads(raw))
                if raw
                else service_account.Credentials.from_service_account_file(path)
            )
            return cls(bucket, storage.Client(credentials=creds, project=creds.project_id))
        try:
            adc, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except google.auth.exceptions.DefaultCredentialsError as exc:
            raise StorageNotConfigured(
                "no Google credentials: on GCP attach a service account to the service; on a "
                "laptop run `gcloud auth application-default login` (a key file is not needed)"
            ) from exc
        signer = os.environ.get("GCS_SIGNER_SERVICE_ACCOUNT", "").strip() or getattr(
            adc, "service_account_email", None
        )
        if not signer or signer == "default":
            # on Compute Engine the email is filled in after the first refresh
            try:
                from google.auth.transport.requests import Request

                adc.refresh(Request())
            except Exception:  # no metadata server here: fall through to the plain message
                pass
            signer = os.environ.get("GCS_SIGNER_SERVICE_ACCOUNT", "").strip() or getattr(
                adc, "service_account_email", None
            )
        if not signer or signer == "default":
            raise StorageNotConfigured(
                "set GCS_SIGNER_SERVICE_ACCOUNT to the service account that signs URLs "
                "(you need Service Account Token Creator on it)"
            )
        client = storage.Client(credentials=adc, project=project or os.environ.get("GCP_PROJECT"))
        return cls(bucket, client, credentials=adc, signer=signer)

    def _signing(self) -> dict[str, Any]:
        """Extra arguments for generate_signed_url: none with a key; with ADC the signer's email and
        a fresh access token, so Google's IAM service signs the URL."""
        if self._credentials is None:
            return {}
        if not self._credentials.valid:
            from google.auth.transport.requests import Request

            self._credentials.refresh(Request())
        return {"service_account_email": self._signer, "access_token": self._credentials.token}

    def presign_put(self, key: str, content_type: str, expires: int = 300) -> SignedUpload:
        url = self.bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires),
            method="PUT",
            content_type=content_type,
            **self._signing(),
        )
        return SignedUpload(url, {"Content-Type": content_type}, expires)

    def presign_get(self, key: str, expires: int = 120, filename: str | None = None) -> str:
        extra: dict[str, Any] = self._signing()
        if filename:
            extra["response_disposition"] = f'attachment; filename="{filename}"'
        return str(
            self.bucket.blob(key).generate_signed_url(
                version="v4", expiration=timedelta(seconds=expires), method="GET", **extra
            )
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.bucket.blob(key).upload_from_string(data, content_type=content_type)

    def get(self, key: str) -> bytes:
        return bytes(self.bucket.blob(key).download_as_bytes())

    def size(self, key: str) -> int | None:
        blob = self.bucket.get_blob(key)
        return int(blob.size) if blob is not None and blob.size is not None else None

    def delete(self, key: str) -> None:
        self.bucket.blob(key).delete()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class LocalBlobStore:
    """In-memory (or a folder) stand-in. Its URLs are `/api/media/blob/<token>` and expire."""

    def __init__(
        self,
        secret: bytes,
        *,
        root: Path | None = None,
        clock: Callable[[], float] = time.time,
        base: str = "/api/media/blob",
    ) -> None:
        self._secret = secret
        self._root = root
        self._clock = clock
        self._base = base
        self._mem: dict[str, bytes] = {}
        self.types: dict[str, str] = {}

    # signed tokens -------------------------------------------------------------------------
    def _token(
        self, method: str, key: str, expires: int, extra: dict[str, Any] | None = None
    ) -> str:
        body = _b64(
            json.dumps(
                {"m": method, "k": key, "e": int(self._clock()) + expires, **(extra or {})},
                separators=(",", ":"),
            ).encode()
        )
        sig = hmac.new(self._secret, body.encode(), hashlib.sha256).digest()
        return f"{body}.{_b64(sig)}"

    def verify(self, token: str, method: str) -> dict[str, Any] | None:
        """The token's claims if it is genuine, unexpired and for this method; else None."""
        body, _, sig = token.partition(".")
        want = hmac.new(self._secret, body.encode(), hashlib.sha256).digest()
        try:
            if not hmac.compare_digest(want, _unb64(sig)):
                return None
            claims = json.loads(_unb64(body))
        except ValueError:
            return None
        if claims.get("m") != method or claims.get("e", 0) < self._clock():
            return None
        return dict(claims)

    # BlobStore -----------------------------------------------------------------------------
    def presign_put(self, key: str, content_type: str, expires: int = 300) -> SignedUpload:
        token = self._token("PUT", key, expires, {"t": content_type})
        return SignedUpload(f"{self._base}/{token}", {"Content-Type": content_type}, expires)

    def presign_get(self, key: str, expires: int = 120, filename: str | None = None) -> str:
        return f"{self._base}/{self._token('GET', key, expires)}"

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.types[key] = content_type
        if self._root is None:
            self._mem[key] = data
            return
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        if self._root is None:
            return self._mem[key]
        return (self._root / key).read_bytes()

    def size(self, key: str) -> int | None:
        if self._root is None:
            return len(self._mem[key]) if key in self._mem else None
        path = self._root / key
        return path.stat().st_size if path.exists() else None

    def delete(self, key: str) -> None:
        self.types.pop(key, None)
        if self._root is None:
            self._mem.pop(key, None)
        elif (self._root / key).exists():
            (self._root / key).unlink()

    def keys(self) -> list[str]:
        if self._root is None:
            return sorted(self._mem)
        return sorted(
            p.relative_to(self._root).as_posix() for p in self._root.rglob("*") if p.is_file()
        )


def _local_secret() -> bytes:
    secret = os.environ.get("LINK_SECRET")
    return (secret or "dev-only-local-store").encode()


@cache
def audio_store() -> BlobStore:
    """The published-audio bucket: approved audio only."""
    if os.environ.get("GCS_AUDIO_BUCKET"):
        return GcsBlobStore.from_env("GCS_AUDIO")
    if os.environ.get("S3_BUCKET"):
        return S3BlobStore.from_env("S3")
    if os.environ.get("MEDIA_LOCAL_STORE") == "1":
        return LocalBlobStore(_local_secret(), root=Path(".media-local") / "audio")
    raise StorageNotConfigured(
        "GCS_AUDIO_BUCKET or S3_BUCKET is not set (MEDIA_LOCAL_STORE=1 is for dev only)"
    )


def get_audio_store() -> BlobStore:
    return audio_store()
