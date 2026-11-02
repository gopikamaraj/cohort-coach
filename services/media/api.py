"""Downloads from the local media store (development only). A real bucket serves its own signed
URLs, so in production this route has nothing to serve and answers 403."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from services.media.storage import BlobStore, LocalBlobStore, StorageNotConfigured, get_audio_store

router = APIRouter(prefix="/api/media", tags=["media"])


def _store() -> BlobStore | None:
    try:
        return get_audio_store()
    except StorageNotConfigured:
        return None


@router.get("/blob/{token}", include_in_schema=False)
def blob_get(token: str, store: BlobStore | None = Depends(_store)) -> Response:  # noqa: B008
    if isinstance(store, LocalBlobStore):
        claims = store.verify(token, "GET")
        if claims and store.size(claims["k"]) is not None:
            return Response(
                store.get(claims["k"]),
                media_type=store.types.get(claims["k"], "application/octet-stream"),
            )
    raise HTTPException(403, "This link has expired.")
