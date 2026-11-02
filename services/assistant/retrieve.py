"""Retrieval inside one scope: words first, and meaning too when RETRIEVAL=vector (vector.py).

`search` takes a Scope and a query, and reads only the namespaces that scope lists. There is no
namespace argument anywhere, so a question can never widen what is searched: that is the scope
guarantee (tests/assistant/test_leaks.py). Ranking is BM25 over the scope's chunks, with the
heading counted twice. When nothing clears the bar the result is empty and the caller abstains.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from services.assistant.index import INDEX_DIR, Chunk
from services.assistant.scopes import Scope

K1, B = 1.2, 0.75
# A chunk is an answer only if the words it shares with the question are informative for this
# corpus: their summed idf must reach this share of ln(corpus size). It scales with the size of the
# scope, so a small help page and the whole repository are held to the same bar. BM25 only ranks.
MIN_INFO = 0.45
# And it must cover a fair share of what was asked: two stray shared words do not answer a long question.
MIN_COVERAGE = 0.4
MAX_FILE_CHUNKS_PER_PATH = 2  # so one long file does not crowd every other source out

_SPLIT = re.compile(r"[\s,.;:!?()\[\]{}\"'“”‘’।॥/\\|<>=+*&^%$#@~`_-]+")
STOP = frozenset(
    "a an and are as at be by can do does for from how i if in is it its me my of on or our so "
    "that the their them there these this to us was we what when where which who why will with you your "
    "about into than then they not no "
    # polite and question filler: it says nothing about what is asked, so it never counts as a match
    "please kindly tell show explain give thanks thank hello hi "
    "many much should could would take each does did long get need".split()
)


def stem(w: str) -> str:
    """A light stemmer, the same for the pages and the question: mentoring and mentor, approve,
    approving and approved, and plurals meet. It is not a language model; it only trims endings."""
    if not w.isascii() or len(w) <= 3:
        return w  # Hindi and Tamil words are matched as written
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ing") and len(w) > 5:
        w = w[:-3]
    elif w.endswith("ed") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("es") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return w


def tokens(text: str) -> list[str]:
    out = []
    for t in _SPLIT.split(unicodedata.normalize("NFKC", text).lower()):
        if t and t not in STOP:
            out.append(stem(t))
    return out


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    matched: int


def _chunk(d: dict[str, Any]) -> Chunk:
    return Chunk(**d)


@cache
def _load(index_dir: Path, ns: str) -> tuple[Chunk, ...]:
    f = index_dir / f"{ns}.json"
    if not f.exists():
        return ()
    return tuple(_chunk(d) for d in json.loads(f.read_text(encoding="utf-8")))


def reload() -> None:
    """Drop cached indexes (after a rebuild, and in tests)."""
    _load.cache_clear()


def meta(index_dir: Path = INDEX_DIR) -> dict[str, Any]:
    f = index_dir / "META.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    assert isinstance(data, dict)
    return data


def chunks_in(scope: Scope, index_dir: Path = INDEX_DIR) -> list[Chunk]:
    """Every chunk this scope may read: its namespaces and no others."""
    out: list[Chunk] = []
    for ns in scope.namespaces:
        out.extend(_load(index_dir, ns))
    return out


def get_chunk(scope: Scope, chunk_id: str, index_dir: Path = INDEX_DIR) -> Chunk | None:
    """A chunk by id, but only inside the scope (a foreign id returns None)."""
    return next((c for c in chunks_in(scope, index_dir) if c.id == chunk_id), None)


RRF_K = (
    60  # reciprocal-rank fusion: a hit's weight is 1 / (RRF_K + rank) in each list it appears in
)


def search(scope: Scope, query: str, k: int = 5, index_dir: Path = INDEX_DIR) -> list[Hit]:
    """Word hits, merged with meaning hits when the vector flag is on. Both lists are drawn from the
    chunks this scope may read and no others; if the vector side fails, the word hits stand alone."""
    words = _word_search(scope, query, k=max(k, 8), index_dir=index_dir)
    from services.assistant import vector

    if not vector.enabled():
        return _spread(words, k)
    docs = chunks_in(scope, index_dir)
    by_id = {c.id: c for c in docs}
    sem = vector.hits(query, docs, k=max(k, 8), index_dir=index_dir)
    if not sem:
        return _spread(words, k)
    fused: dict[str, float] = {}
    matched: dict[str, int] = {}
    for rank, h in enumerate(words):
        fused[h.chunk.id] = fused.get(h.chunk.id, 0.0) + 1 / (RRF_K + rank)
        matched[h.chunk.id] = h.matched
    for rank, (cid, _) in enumerate(sem):
        fused[cid] = fused.get(cid, 0.0) + 1 / (RRF_K + rank)
    ranked = sorted(fused, key=lambda cid: (-fused[cid], cid))
    return _spread(
        [Hit(by_id[cid], round(fused[cid], 4), matched.get(cid, 0)) for cid in ranked], k
    )


def _spread(hits: list[Hit], k: int) -> list[Hit]:
    out: list[Hit] = []
    per_path: Counter[str] = Counter()
    for h in hits:
        if per_path[h.chunk.path] >= MAX_FILE_CHUNKS_PER_PATH:
            continue
        per_path[h.chunk.path] += 1
        out.append(h)
        if len(out) == k:
            break
    return out


def _word_search(scope: Scope, query: str, k: int, index_dir: Path) -> list[Hit]:
    docs = chunks_in(scope, index_dir)
    q = list(dict.fromkeys(tokens(query)))
    if not docs or not q:
        return []
    bags = [Counter(tokens(c.heading) * 2 + tokens(c.text)) for c in docs]
    lengths = [sum(b.values()) or 1 for b in bags]
    avg = sum(lengths) / len(lengths)
    n = len(docs)
    df = {t: sum(1 for b in bags if t in b) for t in q}
    idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in q}
    bar = MIN_INFO * math.log(max(n, 2))
    need = max(
        2 if len(q) >= 2 else 1, math.ceil(MIN_COVERAGE * len(q))
    )  # a stray word is not an answer
    hits: list[Hit] = []
    for c, b, ln in zip(docs, bags, lengths, strict=True):
        matched = [t for t in q if t in b]
        if len(matched) < need:
            continue
        if sum(idf[t] for t in matched) < bar:
            continue
        s = 0.0
        for t in matched:
            f = b[t]
            s += idf[t] * (f * (K1 + 1)) / (f + K1 * (1 - B + B * ln / avg))
        hits.append(Hit(c, round(s, 4), len(matched)))
    hits.sort(key=lambda h: (-h.score, h.chunk.id))
    return hits[:k]
