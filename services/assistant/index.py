"""Build the assistant's knowledge indexes from allowlisted files, one per namespace.

Run `python scripts/build_assistant_index.py` (the deploy step); the output in
services/assistant/index/ is bundled with the API image, so retrieval works with no network.

* Only files matched by services/assistant/sources.yaml are read, and `deny` wins.
* Every source is scanned first. A secret, a phone number, an email address or a roll number fails
  the build; the message names the file and line and the kind of finding, never the value.
* Text is chunked by heading, then by sentence (a table row is one unit), with stable ids.
* Deck slides carry `slide_no`; video-script segments carry `ts_start` and `ts_end`.
* No embeddings: retrieval is word-based (retrieve.py), so the index is plain JSON.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from services.assistant import claims, rubric

ROOT = Path(__file__).resolve().parents[2]
SOURCES = Path(__file__).with_name("sources.yaml")
INDEX_DIR = Path(__file__).with_name("index")
CHUNK_WORDS = 80
LONG_UNIT_WORDS = 160

# What may never be indexed. Each is (kind, pattern). Findings report the kind, never the value.
FINDINGS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("secret", re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16}")),
    ("secret", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),  # a Telegram bot token
    ("secret", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}")),  # a signed token
    (
        "secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|subscription-key)\b[\"']?\s*[:=]\s*[\"']?"
            r"[A-Za-z0-9_\-]{20,}"
        ),
    ),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?<![\d.])(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")),
    ("roll number", re.compile(r"(?i)\broll\s*(?:no\.?|number|#)\s*[:=#-]?\s*\d{1,6}\b")),
)
# Not a person: obvious placeholders, and Google service-account identifiers (a cloud role such as
# "api@project.iam.gserviceaccount.com" names software, not an individual). Any other address fails.
PLACEHOLDER_EMAIL = re.compile(
    r"@(?:example\.(?:com|org|net)|domain\.tld|[a-z0-9-]+\.iam\.gserviceaccount\.com)\b", re.I
)

_SENTENCE = re.compile(r"(?<=[.!?।])\s+(?=[A-Z0-9\"“(ऀ-ॿ஀-௿])")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SLIDE = re.compile(r"^##\s+Slide\s+(\d+):\s*(.*)$")
_SEGMENT = re.compile(r"^\[(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\]\s+([^:]+):\s*(.*)$")


class IndexBuildError(Exception):
    """The build found something that must not be indexed, or a source it cannot read."""


@dataclass
class Chunk:
    id: str
    ns: str
    path: str
    heading: str
    line: int
    text: str
    kind: str = "file"  # file, slide or video
    slide_no: int | None = None
    ts_start: int | None = None  # seconds into the video
    ts_end: int | None = None
    section: str | None = None


@dataclass
class Built:
    chunks: dict[str, list[Chunk]] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    # What the server reads at run time besides the chunks (docs/ is not in the API image):
    # the rubric rows, the deck and video facts, and the question banks.
    extras: dict[str, Any] = field(default_factory=dict)


def seconds(mmss: str) -> int:
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def slug(text: str) -> str:
    s = re.sub(r"[^\wऀ-ॿ஀-௿]+", "-", text.lower()).strip("-")
    return s or "section"


def words(text: str) -> int:
    return len(text.split())


def scan(path: str, text: str) -> list[str]:
    """Findings in one file as "path:line kind" strings. Values are never included."""
    out: list[str] = []
    for n, line in enumerate(text.splitlines(), 1):
        for kind, pat in FINDINGS:
            for m in pat.finditer(line):
                if kind == "email" and PLACEHOLDER_EMAIL.search(m.group(0)):
                    continue
                out.append(f"{path}:{n} {kind}")
    return out


def _units(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Sentences of the prose in one section; a table row, a list item or a code line stands alone."""
    units: list[tuple[int, str]] = []
    para: list[tuple[int, str]] = []

    def flush() -> None:
        if not para:
            return
        text = " ".join(t for _, t in para)
        for s in _SENTENCE.split(text):
            if s.strip():
                units.append((para[0][0], s.strip()))
        para.clear()

    in_code = False
    for n, raw in lines:
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code or not line.strip():
            flush()
            continue
        stripped = line.strip()
        if stripped.startswith("|"):
            flush()
            if not re.fullmatch(r"\|[\s:|-]+\|?", stripped):  # skip a table's divider row
                units.append((n, stripped))
        elif re.match(r"([-*]|\d+\.)\s", stripped):
            flush()
            units.append((n, stripped))
        else:
            para.append((n, stripped))
    flush()
    return units


def chunk_markdown(ns: str, path: str, text: str) -> list[Chunk]:
    sections: list[tuple[str, int, list[tuple[int, str]]]] = []
    trail: list[tuple[int, str]] = []
    cur: tuple[str, int, list[tuple[int, str]]] = ("", 1, [])
    in_code = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        h = None if in_code else _HEADING.match(line)
        if h:
            if cur[2]:
                sections.append(cur)
            level, title = len(h.group(1)), h.group(2)
            trail = [(lv, t) for lv, t in trail if lv < level] + [(level, title)]
            cur = (" > ".join(t for _, t in trail), n, [])
        else:
            cur[2].append((n, line))
    if cur[2]:
        sections.append(cur)

    chunks: list[Chunk] = []
    for heading, start, lines in sections:
        base = f"{ns}:{path}#{slug(heading)}"
        pending: list[tuple[int, str]] = []
        count = 0

        def emit(
            units: list[tuple[int, str]],
            base: str = base,
            heading: str = heading,
            start: int = start,
        ) -> None:
            n_in = sum(1 for c in chunks if c.id.startswith(base + ":"))
            chunks.append(
                Chunk(
                    id=f"{base}:{n_in}",
                    ns=ns,
                    path=path,
                    heading=heading or Path(path).stem,
                    line=units[0][0] if units else start,
                    text=" ".join(t for _, t in units),
                )
            )

        for unit in _units(lines):
            w = words(unit[1])
            if pending and (count + w > CHUNK_WORDS or w > LONG_UNIT_WORDS):
                emit(pending)
                pending, count = [], 0
            pending.append(unit)
            count += w
        if pending:
            emit(pending)
    return chunks


def chunk_slides(ns: str, path: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur: tuple[int, str, int, list[str]] | None = None
    for n, line in enumerate(text.splitlines(), 1):
        m = _SLIDE.match(line)
        if m:
            if cur:
                chunks.append(_slide(ns, path, cur))
            cur = (int(m.group(1)), m.group(2).strip(), n, [])
        elif cur is not None:
            cur[3].append(line)
    if cur:
        chunks.append(_slide(ns, path, cur))
    return chunks


def _slide(ns: str, path: str, cur: tuple[int, str, int, list[str]]) -> Chunk:
    no, title, line, body = cur
    return Chunk(
        id=f"{ns}:{path}#slide-{no}",
        ns=ns,
        path=path,
        heading=f"Slide {no}: {title}",
        line=line,
        text=" ".join(t.strip() for t in body if t.strip()),
        kind="slide",
        slide_no=no,
    )


def chunk_video(ns: str, path: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for n, line in enumerate(text.splitlines(), 1):
        m = _SEGMENT.match(line.strip())
        if not m:
            continue
        a, b = seconds(m.group(1)), seconds(m.group(2))
        chunks.append(
            Chunk(
                id=f"{ns}:{path}#t-{m.group(1)}",
                ns=ns,
                path=path,
                heading=f"Video {m.group(1)} {m.group(3).strip()}",
                line=n,
                text=m.group(4).strip(),
                kind="video",
                ts_start=a,
                ts_end=b,
                section=m.group(3).strip(),
            )
        )
    return chunks


CHUNKERS = {"markdown": chunk_markdown, "slides": chunk_slides, "video": chunk_video}


def load_sources(path: Path = SOURCES) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _denied(rel: str, deny: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(Path(rel).name, p) for p in deny)


def expand(root: Path, patterns: list[str], deny: list[str]) -> list[str]:
    found: set[str] = set()
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            hits = [p for p in root.glob(pat) if p.is_file()]
        else:
            hits = [root / pat] if (root / pat).is_file() else []
        for p in hits:
            rel = p.relative_to(root).as_posix()
            if p.suffix.lower() == ".md" and not _denied(rel, deny):
                found.add(rel)
    return sorted(found)


def build(root: Path = ROOT, sources: dict[str, Any] | None = None) -> Built:
    spec = sources or load_sources()
    deny = list(spec.get("deny", []))
    out = Built()
    findings: list[str] = []
    digest = hashlib.sha256()
    for name, ns_spec in spec["namespaces"].items():
        ns = ns_spec.get("into", name)
        kind = ns_spec["kind"]
        out.chunks.setdefault(ns, [])
        for rel in expand(root, list(ns_spec["files"]), deny):
            text = (root / rel).read_text(encoding="utf-8")
            findings.extend(scan(rel, text))
            digest.update(rel.encode() + b"\0" + text.encode("utf-8") + b"\0")
            out.chunks[ns].extend(CHUNKERS[kind](ns, rel, text))
    extras_files = _extras(root, out, digest, findings)
    if findings:
        raise IndexBuildError(
            "refusing to index files with personal data or secrets (values not shown):\n  "
            + "\n  ".join(sorted(set(findings)))
        )
    ids = [c.id for cs in out.chunks.values() for c in cs]
    if len(ids) != len(set(ids)):
        raise IndexBuildError("chunk ids are not unique")
    out.meta = {
        "content_hash": digest.hexdigest(),
        "chunks": {ns: len(cs) for ns, cs in sorted(out.chunks.items())},
        "extras": extras_files,
    }
    return out


SCOPES_NAME = "assistant_scopes.yaml"
QUESTIONS = "docs/assistant_questions"
VIDEO_JSON = "docs/submission/video.json"
DECK_PDF = "docs/submission/deck.pdf"


def _extras(root: Path, out: Built, digest: Any, findings: list[str]) -> list[str]:
    """Bundle the rubric rows (each with any deck or video wording that claims more), the deck and
    video facts, and every role's question bank. Their sources count toward the content hash."""
    judge = out.chunks.get("judge", [])
    slides = {
        c.slide_no: f"{c.heading} {c.text}" for c in judge if c.kind == "slide" and c.slide_no
    }
    segments = {
        f"{(c.ts_start or 0) // 60:02d}:{(c.ts_start or 0) % 60:02d}": c
        for c in judge
        if c.kind == "video"
    }
    rows: list[rubric.Row] = []
    rmap = root / "docs" / "RUBRIC_MAP.md"
    if rmap.exists():
        rows = rubric.parse(rmap.read_text(encoding="utf-8"))
    seg_text = {t: f"{c.section} {c.text}" for t, c in segments.items()}
    differs = claims.mismatches(rows, slides, seg_text)
    out.extras["rubric"] = [
        {**r.to_dict(), "differs": [m.__dict__ for m in differs if m.row == r.id]} for r in rows
    ]
    video: dict[str, Any] = {}
    vfile = root / VIDEO_JSON
    if vfile.exists():
        raw = vfile.read_text(encoding="utf-8")
        digest.update(VIDEO_JSON.encode() + b"\0" + raw.encode("utf-8") + b"\0")
        video = json.loads(raw)
    scopes_file = root / SCOPES_NAME
    if scopes_file.exists():  # a copy is bundled, so the image needs no file outside services/
        digest.update(SCOPES_NAME.encode() + b"\0" + scopes_file.read_bytes() + b"\0")
    has_pdf = (root / DECK_PDF).exists()
    digest.update(f"deck_pdf={has_pdf}".encode())
    out.extras["submission"] = {
        "video": video,
        "deck_pdf": has_pdf,
        "slides": {
            str(n): c.heading.split(": ", 1)[-1]
            for n, c in ((c.slide_no, c) for c in judge if c.kind == "slide")
        },
        "segments": {
            t: {"end": c.ts_end, "section": c.section} for t, c in sorted(segments.items())
        },
        "provisional": not (has_pdf and bool(video.get("final"))),
        "forbidden": claims.forbidden(slides, seg_text),
        "late": claims.late_claims(rows),
    }
    banks: dict[str, Any] = {}
    for f in sorted((root / QUESTIONS).glob("*.json")) if (root / QUESTIONS).exists() else []:
        rel = f.relative_to(root).as_posix()
        raw = f.read_text(encoding="utf-8")
        findings.extend(scan(rel, raw))
        digest.update(rel.encode() + b"\0" + raw.encode("utf-8") + b"\0")
        banks[f.stem] = json.loads(raw)
    out.extras["questions"] = banks
    return sorted(out.extras)


def git_sha(root: Path = ROOT) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def write(built: Built, out_dir: Path = INDEX_DIR, sha: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    for ns, chunks in built.chunks.items():
        (out_dir / f"{ns}.json").write_text(
            json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8",
        )
    for name, data in built.extras.items():
        (out_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
        )
    scopes_file = ROOT / SCOPES_NAME
    if scopes_file.exists():
        shutil.copyfile(scopes_file, out_dir / SCOPES_NAME)
    meta = dict(built.meta)
    meta["source_commit"] = sha
    (out_dir / "META.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def is_current(out_dir: Path = INDEX_DIR, root: Path = ROOT) -> bool:
    """True if the bundled index was built from the sources as they are now."""
    meta_file = out_dir / "META.json"
    if not meta_file.exists():
        return False
    return bool(
        json.loads(meta_file.read_text(encoding="utf-8"))["content_hash"]
        == build(root).meta["content_hash"]
    )
