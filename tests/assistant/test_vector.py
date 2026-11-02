"""Meaning-based retrieval: off by default, scoped like words, and never able to break an answer."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path

import httpx
import numpy as np
import pytest

from services.assistant import retrieve, vector
from services.assistant.scopes import scopes

DIMS = 8
NONSENSE = "zxqv blorptastic wumbleflux"
QUESTION = "how do I start a practice class with the children"


def unit(i: int) -> list[float]:
    v = [0.0] * DIMS
    v[i % DIMS] = 1.0
    return v


class FakeEmbedder:
    """A query maps to the vector the test chooses; nothing is sent anywhere."""

    def __init__(self, qvec: list[float] | None = None, fail: bool = False) -> None:
        self.qvec, self.fail, self.calls = qvec or unit(0), fail, 0

    def documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [unit(i) for i, _ in enumerate(texts)]

    def query(self, text: str) -> list[float]:
        self.calls += 1
        if self.fail:
            raise vector.EmbedError("down")
        return self.qvec


class MapStore:
    """Chunk id -> vector, searched with a plain dot product (as the local store does)."""

    def __init__(self, vecs: dict[str, list[float]]) -> None:
        self.vecs = vecs

    def search(
        self, qvec: Sequence[float], allowed: Sequence[object], k: int
    ) -> list[tuple[str, float]]:
        out = [(cid, float(np.dot(v, qvec))) for cid, v in self.vecs.items()]
        return sorted(out, key=lambda t: -t[1])[:k]


@pytest.fixture(autouse=True)
def reset(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for n in ("RETRIEVAL", "GEMINI_API_KEY", "VECTOR_STORE"):
        monkeypatch.delenv(n, raising=False)
    vector.set_backends(None, None)
    yield
    vector.set_backends(None, None)


def chunk_ids(role: str) -> list[str]:
    return [c.id for c in retrieve.chunks_in(scopes()[role])]


def test_vector_retrieval_is_off_unless_asked_for(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = FakeEmbedder()
    vector.set_backends(emb, MapStore({}))
    before = retrieve.search(scopes()["teacher"], QUESTION, k=3)
    assert emb.calls == 0 and before  # the flag is off: the embedder is never called
    monkeypatch.setenv("RETRIEVAL", "vector")
    assert vector.enabled()


def test_a_meaning_hit_is_found_when_the_words_do_not_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = chunk_ids("teacher")[3]
    vector.set_backends(FakeEmbedder(unit(5)), MapStore({target: unit(5)}))
    assert retrieve.search(scopes()["teacher"], NONSENSE, k=3) == []  # words alone find nothing
    monkeypatch.setenv("RETRIEVAL", "vector")
    hits = retrieve.search(scopes()["teacher"], NONSENSE, k=3)
    assert [h.chunk.id for h in hits] == [target]


def test_a_vector_hit_outside_the_scope_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVAL", "vector")
    foreign = next(i for i in chunk_ids("judge") if i not in set(chunk_ids("teacher")))
    vector.set_backends(FakeEmbedder(unit(1)), MapStore({foreign: unit(1)}))
    assert retrieve.search(scopes()["teacher"], NONSENSE, k=3) == []


def test_a_weak_match_is_not_a_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVAL", "vector")
    target = chunk_ids("teacher")[0]
    weak = [0.3] + [0.0] * (DIMS - 1)
    vector.set_backends(FakeEmbedder(unit(0)), MapStore({target: weak}))
    assert retrieve.search(scopes()["teacher"], NONSENSE, k=3) == []


def test_a_failing_embedder_leaves_the_word_hits_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    plain = [h.chunk.id for h in retrieve.search(scopes()["teacher"], QUESTION, k=3)]
    monkeypatch.setenv("RETRIEVAL", "vector")
    vector.set_backends(FakeEmbedder(fail=True), MapStore({}))
    assert [h.chunk.id for h in retrieve.search(scopes()["teacher"], QUESTION, k=3)] == plain


def test_words_and_meaning_are_fused_and_a_chunk_in_both_ranks_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    words = retrieve._word_search(scopes()["teacher"], QUESTION, k=8, index_dir=retrieve.INDEX_DIR)
    other = next(i for i in chunk_ids("teacher") if i not in {h.chunk.id for h in words})
    monkeypatch.setenv("RETRIEVAL", "vector")
    both = words[1].chunk.id
    vector.set_backends(
        FakeEmbedder(unit(2)), MapStore({both: unit(2), other: [0.6, 0.0, 0.8] + [0.0] * 5})
    )
    fused = [h.chunk.id for h in retrieve.search(scopes()["teacher"], QUESTION, k=5)]
    assert fused[0] == both and other in fused


# --- the Gemini request -------------------------------------------------------------------------


def test_gemini_requests_carry_the_key_in_a_header_and_normalise_the_vectors() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        body = json.loads(req.content)
        if req.url.path.endswith(":batchEmbedContents"):
            return httpx.Response(
                200, json={"embeddings": [{"values": [3.0, 4.0]} for _ in body["requests"]]}
            )
        return httpx.Response(200, json={"embedding": {"values": [3.0, 4.0]}})

    emb = vector.GeminiEmbedder(
        "SECRET-KEY", dims=2, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert emb.query("hello") == pytest.approx([0.6, 0.8])
    assert emb.documents(["a", "b"]) == [pytest.approx([0.6, 0.8])] * 2
    q, d = seen
    assert q.headers["x-goog-api-key"] == "SECRET-KEY" and "SECRET-KEY" not in str(q.url)
    assert json.loads(q.content)["taskType"] == "RETRIEVAL_QUERY"
    assert json.loads(d.content)["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"
    assert json.loads(q.content)["outputDimensionality"] == 2


def test_an_embedding_failure_is_an_error_that_never_shows_the_key() -> None:
    emb = vector.GeminiEmbedder(
        "SECRET-KEY",
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403))),
    )
    with pytest.raises(vector.EmbedError) as e:
        emb.query("hi")
    assert "SECRET-KEY" not in str(e.value) and "403" in str(e.value)


def test_a_wrong_number_of_vectors_is_refused() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"embeddings": []}))
    emb = vector.GeminiEmbedder("k", client=httpx.Client(transport=transport))
    with pytest.raises(vector.EmbedError):
        emb.documents(["a"])


# --- stores -------------------------------------------------------------------------------------


def test_the_local_store_round_trips_and_ignores_ids_that_are_not_allowed(tmp_path: Path) -> None:
    chunks = retrieve.chunks_in(scopes()["teacher"])[:3]
    path = tmp_path / "vectors.npz"
    ids = [c.id for c in chunks] + ["stale-id"]
    vector.LocalStore.write(path, ids, [unit(0), unit(1), unit(2), unit(1)], "m")
    got = vector.LocalStore(path).search(unit(1), chunks, k=3)
    assert got[0][0] == chunks[1].id and all(cid != "stale-id" for cid, _ in got)


def test_a_missing_vectors_file_means_no_hits(tmp_path: Path) -> None:
    store = vector.LocalStore(tmp_path / "none.npz")
    assert store.search(unit(0), retrieve.chunks_in(scopes()["teacher"]), 3) == []


class FakeDoc:
    def __init__(self, d: dict[str, object]) -> None:
        self.d = d

    def to_dict(self) -> dict[str, object]:
        return self.d


class FakeQuery:
    def __init__(self, log: list[dict[str, object]]) -> None:
        self.log = log

    def find_nearest(self, **kw: object) -> FakeQuery:
        self.log.append(kw)
        return self

    def stream(self) -> list[FakeDoc]:
        return [FakeDoc({"id": "c1", "distance": 0.1})]


class FakeCollection:
    def __init__(self) -> None:
        self.log: list[dict[str, object]] = []
        self.wheres: list[tuple[str, str, list[str]]] = []

    def where(self, field: str, op: str, value: list[str]) -> FakeQuery:
        self.wheres.append((field, op, value))
        return FakeQuery(self.log)


class FakeClient:
    def __init__(self) -> None:
        self.col = FakeCollection()

    def collection(self, name: str) -> FakeCollection:
        return self.col


def test_the_firestore_store_searches_only_the_scopes_namespaces() -> None:
    pytest.importorskip("google.cloud.firestore_v1")
    client = FakeClient()
    store = vector.FirestoreStore(client=client)
    allowed = retrieve.chunks_in(scopes()["teacher"])
    got = store.search(unit(0), allowed, k=3)
    assert got == [("c1", pytest.approx(0.9))]
    field, op, spaces = client.col.wheres[0]
    assert (field, op) == ("ns", "in") and set(spaces) == {c.ns for c in allowed}
    assert client.col.log[0]["limit"] == 3
