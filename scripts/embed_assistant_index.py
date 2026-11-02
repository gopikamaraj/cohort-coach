"""Embed the assistant's chunks for meaning-based retrieval (offline, after the index build).

    python scripts/embed_assistant_index.py              write index/vectors.npz
    python scripts/embed_assistant_index.py --firestore  also write the vectors to Firestore
    python scripts/embed_assistant_index.py --check      exit 1 if vectors.npz misses chunks

Needs GEMINI_API_KEY in .env. The free tier is enough for the ~1,200 chunks (a dozen batch calls);
the count is printed first. The chunks are repository and help pages, never user data. Turn the
feature on with RETRIEVAL=vector; with it off nothing here is used.

Firestore needs the vector index once (field `embedding`, flat, dimension = GEMINI_EMBED_DIMS, with
`ns` as an equality field):
    gcloud firestore indexes composite create --collection-group=assistant_chunks \
      --query-scope=COLLECTION --field-config=field-path=ns,order=ASCENDING \
      --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402
from services.assistant import retrieve, vector  # noqa: E402
from services.assistant.index import INDEX_DIR  # noqa: E402
from services.assistant.scopes import scopes  # noqa: E402

PATH = INDEX_DIR / "vectors.npz"


def all_chunks() -> list[vector.Chunk]:
    seen: dict[str, vector.Chunk] = {}
    for sc in scopes().values():
        for c in retrieve.chunks_in(sc):
            seen.setdefault(c.id, c)
    return list(seen.values())


def main(argv: list[str]) -> int:
    load_env()
    chunks = all_chunks()
    if "--check" in argv:
        ids, mat = vector._load_local(PATH)
        ok = mat is not None and set(ids) >= {c.id for c in chunks}
        print(
            "vectors cover every chunk" if ok else "vectors are missing or stale: run this script"
        )
        return 0 if ok else 1
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY is empty: put the key in .env and run again")
        return 2
    model = os.environ.get("GEMINI_EMBED_MODEL", vector.DEFAULT_MODEL)
    dims = int(os.environ.get("GEMINI_EMBED_DIMS", vector.DEFAULT_DIMS))
    batches = -(-len(chunks) // vector.BATCH)
    print(f"{len(chunks)} chunks, {batches} embedding calls, model {model}, {dims} dimensions")
    emb = vector.GeminiEmbedder(key, model, dims)
    vecs = emb.documents([vector.chunk_text(c) for c in chunks])
    vector.LocalStore.write(PATH, [c.id for c in chunks], vecs, model)
    print(f"wrote {PATH.relative_to(ROOT)} ({PATH.stat().st_size // 1024} KB)")
    if "--firestore" in argv:
        store = vector.FirestoreStore()
        store.upsert([(c.id, c.ns, v) for c, v in zip(chunks, vecs, strict=True)])
        print(f"wrote {len(chunks)} documents to Firestore")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
