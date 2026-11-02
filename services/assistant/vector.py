"""Meaning-based retrieval for the assistant, behind a flag (RETRIEVAL=vector; off by default).

Words alone miss a Hindi or Tamil question about an English help page, so a question can also be
matched by meaning: an embedding of the (already masked) question is compared with embeddings of the
chunks. Embeddings come from the Gemini API (`gemini-embedding-001`, key in GEMINI_API_KEY). The
vectors are stored in one of two places (VECTOR_STORE):

* `local` (default): `services/assistant/index/vectors.npz`, built offline by
  `scripts/embed_assistant_index.py` and bundled with the API image. Cosine runs in memory.
* `firestore`: the same vectors in a Firestore collection, searched with its nearest-neighbour query.

Nothing here decides what a person may read. `retrieve.search` passes in the chunks the scope allows,
and a vector hit outside that list is dropped, so the scope guarantee is the same as for words. Any
failure (no key, network, an empty store) returns no vector hits and the caller keeps the word hits.
The chunks are repository and help pages; the only user text sent out is the masked question.
"""

from __future__ import annotations

import importlib
import logging
import math
import os
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import Any, Protocol

import httpx
import numpy as np

from services.assistant.index import INDEX_DIR, Chunk

log = logging.getLogger("assistant.vector")

API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-embedding-001"
DEFAULT_DIMS = 768
BATCH = 100
TIMEOUT_S = 6.0
# A hit must be this similar to count. Chosen by eye, not tuned: there is no labelled set for it yet,
# so it errs towards "no hit" (the assistant then says it cannot answer) rather than a wrong page.
MIN_COSINE = 0.62
FIRESTORE_COLLECTION = "assistant_chunks"


class EmbedError(RuntimeError):
    """The embedding service could not be used. The message never contains the key."""


def normalise(v: Sequence[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def chunk_text(c: Chunk) -> str:
    return f"{c.heading}\n{c.text}" if c.heading else c.text


class Embedder(Protocol):
    def documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def query(self, text: str) -> list[float]: ...


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        dims: int = DEFAULT_DIMS,
        client: httpx.Client | None = None,
    ) -> None:
        self._key, self.model, self.dims = api_key, model, dims
        self._http = client or httpx.Client(timeout=TIMEOUT_S)

    def _post(self, op: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            r = self._http.post(
                f"{API}/models/{self.model}:{op}", json=body, headers={"x-goog-api-key": self._key}
            )
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise EmbedError(f"embedding request failed ({status or type(e).__name__})") from None
        assert isinstance(data, dict)
        return data

    def _request(self, text: str, task: str) -> dict[str, Any]:
        return {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task,
            "outputDimensionality": self.dims,
        }

    def documents(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            part = texts[i : i + BATCH]
            data = self._post(
                "batchEmbedContents",
                {"requests": [self._request(t, "RETRIEVAL_DOCUMENT") for t in part]},
            )
            vecs = [e["values"] for e in data.get("embeddings", [])]
            if len(vecs) != len(part):
                raise EmbedError("embedding service returned the wrong number of vectors")
            out += [normalise(v) for v in vecs]
        return out

    def query(self, text: str) -> list[float]:
        data = self._post("embedContent", self._request(text, "RETRIEVAL_QUERY"))
        try:
            return normalise(data["embedding"]["values"])
        except (KeyError, TypeError):
            raise EmbedError("embedding service returned no vector") from None


class Store(Protocol):
    def search(
        self, qvec: Sequence[float], allowed: Sequence[Chunk], k: int
    ) -> list[tuple[str, float]]: ...


class LocalStore:
    """Vectors in one .npz next to the chunk files: ids, float16 matrix, model and dims."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def write(path: Path, ids: Sequence[str], vecs: Sequence[Sequence[float]], model: str) -> None:
        np.savez_compressed(
            path,
            ids=np.array(list(ids)),
            mat=np.array(vecs, dtype=np.float16),
            model=np.array(model),
        )
        _load_local.cache_clear()

    def search(
        self, qvec: Sequence[float], allowed: Sequence[Chunk], k: int
    ) -> list[tuple[str, float]]:
        ids, mat = _load_local(self.path)
        if mat is None or mat.shape[1] != len(qvec):
            return []
        want = {c.id for c in allowed}
        rows = [i for i, cid in enumerate(ids) if cid in want]  # a stale or foreign id is ignored
        if not rows:
            return []
        sims = mat[rows].astype(np.float32) @ np.asarray(qvec, dtype=np.float32)
        order = np.argsort(-sims)[:k]
        return [(ids[rows[j]], float(sims[j])) for j in order]


@cache
def _load_local(path: Path) -> tuple[tuple[str, ...], Any]:
    if not path.exists():
        return (), None
    with np.load(path, allow_pickle=False) as z:
        return tuple(str(x) for x in z["ids"]), z["mat"]


class FirestoreStore:
    """The same vectors in Firestore. `client` is injected in tests; the SDK is imported only here."""

    def __init__(self, client: Any = None, collection: str = FIRESTORE_COLLECTION) -> None:
        if client is None:
            firestore = importlib.import_module(
                "google.cloud.firestore"
            )  # lazy: optional dependency

            client = firestore.Client(project=os.environ.get("FIRESTORE_PROJECT") or None)
        self._col = client.collection(collection)

    def upsert(self, rows: Sequence[tuple[str, str, Sequence[float]]]) -> None:
        Vector = importlib.import_module("google.cloud.firestore_v1.vector").Vector

        for cid, ns, vec in rows:
            self._col.document(cid.replace("/", "_")).set(
                {"id": cid, "ns": ns, "embedding": Vector(list(vec))}
            )

    def search(
        self, qvec: Sequence[float], allowed: Sequence[Chunk], k: int
    ) -> list[tuple[str, float]]:
        DistanceMeasure = importlib.import_module(
            "google.cloud.firestore_v1.base_vector_query"
        ).DistanceMeasure
        Vector = importlib.import_module("google.cloud.firestore_v1.vector").Vector

        spaces = sorted({c.ns for c in allowed})
        if not spaces:
            return []
        q = self._col.where("ns", "in", spaces[:30]).find_nearest(
            vector_field="embedding",
            query_vector=Vector(list(qvec)),
            distance_measure=DistanceMeasure.COSINE,
            limit=k,
            distance_result_field="distance",
        )
        out = []
        for d in q.stream():
            data = d.to_dict()
            out.append(
                (str(data["id"]), 1.0 - float(data["distance"]))
            )  # cosine distance -> similarity
        return out


# --- wiring -------------------------------------------------------------------------------------

_embedder: Embedder | None = None
_store: Store | None = None


def set_backends(embedder: Embedder | None, store: Store | None) -> None:
    """For tests: use these instead of the environment's. Pass None, None to go back."""
    global _embedder, _store
    _embedder, _store = embedder, store


def enabled() -> bool:
    return os.environ.get("RETRIEVAL", "off").lower() == "vector" and (
        _embedder is not None or bool(os.environ.get("GEMINI_API_KEY"))
    )


def _backends(index_dir: Path) -> tuple[Embedder, Store]:
    global _embedder, _store
    if _embedder is None:
        _embedder = GeminiEmbedder(
            os.environ["GEMINI_API_KEY"],
            os.environ.get("GEMINI_EMBED_MODEL", DEFAULT_MODEL),
            int(os.environ.get("GEMINI_EMBED_DIMS", DEFAULT_DIMS)),
        )
    if _store is None:
        kind = os.environ.get("VECTOR_STORE", "local").lower()
        _store = FirestoreStore() if kind == "firestore" else LocalStore(index_dir / "vectors.npz")
    return _embedder, _store


def hits(
    query: str, allowed: Sequence[Chunk], k: int, index_dir: Path = INDEX_DIR
) -> list[tuple[str, float]]:
    """(chunk id, cosine) for the best matches among `allowed`, best first. [] on any failure."""
    if not enabled() or not allowed or not query.strip():
        return []
    try:
        embedder, store = _backends(index_dir)
        qvec = embedder.query(query)
        ok = {c.id for c in allowed}
        found = [
            (cid, s)
            for cid, s in store.search(qvec, allowed, k * 2)
            if cid in ok and s >= MIN_COSINE
        ]
        return found[:k]
    except Exception as e:  # noqa: BLE001  retrieval never breaks the answer; words still work
        log.warning("vector retrieval unavailable: %s", type(e).__name__)
        return []
