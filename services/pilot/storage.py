"""Object storage for the pilot: two private buckets, short-lived signed URLs, no public URL.

`S3BlobStore` talks to any S3-compatible service. `LocalBlobStore` is for tests and for local
development only (the pilot refuses to start without a sheets bucket unless PILOT_LOCAL_STORE=1):
it signs its URLs the same way, so expiry is testable. Neither store ever returns a bucket URL
that works without a signature.
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


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class LocalBlobStore:
    """In-memory (or a folder) stand-in. Its URLs are `/api/pilot/blob/<token>` and expire."""

    def __init__(
        self,
        secret: bytes,
        *,
        root: Path | None = None,
        clock: Callable[[], float] = time.time,
        base: str = "/api/pilot/blob",
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
    secret = os.environ.get("PILOT_TOKEN_SECRET") or os.environ.get("LINK_SECRET")
    return (secret or "dev-only-local-store").encode()


@cache
def sheets_store() -> BlobStore:
    """The private bucket for answer-sheet photos. Never the published-audio bucket."""
    if os.environ.get("S3_SHEETS_BUCKET"):
        if os.environ.get("S3_SHEETS_BUCKET") == os.environ.get("S3_BUCKET"):
            raise StorageNotConfigured("S3_SHEETS_BUCKET must differ from S3_BUCKET")
        return S3BlobStore.from_env("S3_SHEETS")
    if os.environ.get("PILOT_LOCAL_STORE") == "1":
        return LocalBlobStore(_local_secret(), root=Path(".pilot-local") / "sheets")
    raise StorageNotConfigured("S3_SHEETS_BUCKET is not set (PILOT_LOCAL_STORE=1 is for dev only)")


@cache
def audio_store() -> BlobStore:
    """The published-audio bucket: approved audio only."""
    if os.environ.get("S3_BUCKET"):
        return S3BlobStore.from_env("S3")
    if os.environ.get("PILOT_LOCAL_STORE") == "1":
        return LocalBlobStore(_local_secret(), root=Path(".pilot-local") / "audio")
    raise StorageNotConfigured("S3_BUCKET is not set (PILOT_LOCAL_STORE=1 is for dev only)")


def get_sheets_store() -> BlobStore:
    return sheets_store()


def get_audio_store() -> BlobStore:
    return audio_store()
