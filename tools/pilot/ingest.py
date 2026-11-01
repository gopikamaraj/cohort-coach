"""Tidy the pilot sheet photos, read them, and write the answer file. LOCAL ONLY.

    python tasks.py pilot-ingest [--no-ai] [--max-usd 3] [--folder data/pilot]

Reads data/pilot/raw/, writes data/pilot/sheets/{class}-roll{NN}.jpg, pilot_answers.json and
ingest_report.md, and (only when hand-keyed truth exists) docs/evidence/pilot_reading_accuracy.md,
which holds counts and nothing per child. Idempotent. The only network steps are the two optional
AI steps (call 15 header and name scan, call 8 reading), cached by image hash and cost-capped.
Nothing arithmetic is done here: the engine marks every answer and applies the 2-item rule.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.model import Form  # noqa: E402
from services.pilot_demo import answers as ans  # noqa: E402
from services.pilot_demo import numwords  # noqa: E402
from services.pilot_demo.config import (  # noqa: E402
    Manifest,
    PilotClass,
    form_for,
    load_manifest,
    read_form_for,
)

LONG_EDGE = 1600
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
NAME_RE = re.compile(r"(?P<cls>[A-Za-z0-9]{1,8}?)[-_ ]*roll[-_ ]*(?P<roll>\d{1,3})", re.I)
NEAR_BITS = 3  # perceptual hash bits apart that still count as the same photo
Box = tuple[float, float, float, float]


# --- the two optional AI steps, behind seams so tests use fakes ---------------------------


@dataclass(frozen=True)
class Scan:
    class_code: str | None
    roll: int | None
    name_present: bool
    name_boxes: tuple[Box, ...]
    words: tuple[str | None, str | None] = (None, None)  # number words in dictation boxes 1, 2


@dataclass(frozen=True)
class ReadOut:
    texts: list[str]
    confidences: list[float]
    statuses: list[str]
    cost_usd: float = 0.0


class Scanner(Protocol):
    def scan(self, jpeg: bytes) -> Scan | None: ...


class Reader(Protocol):
    def read(self, jpeg: bytes, form: Form) -> ReadOut | None: ...


class LiveScanner:
    """Call 15 through the product's own client (audited, prompt-versioned)."""

    def __init__(self) -> None:
        from ai.client import CallContext

        self.ctx = CallContext(mode="live")

    def scan(self, jpeg: bytes) -> Scan | None:
        from ai.client import CallInput, run_call
        from ai.schemas import PilotSheetScan

        run = run_call(
            15,
            CallInput(trusted={}, images=[("image/jpeg", base64.b64encode(jpeg).decode())]),
            context=self.ctx,
        )
        out = run.output
        if not run.ok or not isinstance(out, PilotSheetScan):
            return None
        boxes = tuple(
            (b[0], b[1], b[2], b[3])
            for b in out.name_boxes
            if len(b) == 4 and all(0.0 <= v <= 1.0 for v in b) and b[0] < b[2] and b[1] < b[3]
        )
        head = (out.class_code or "").split("-")[0].strip()  # the box may read "3A-04"
        code = head if re.fullmatch(r"[A-Za-z0-9]{1,8}", head) else None
        roll = out.roll if out.roll and 1 <= out.roll <= 99 else None
        words = tuple(
            w.strip()[:60] if w and w.strip() else None for w in (out.box1_words, out.box2_words)
        )
        return Scan(code, roll, out.name_present, boxes, words)  # type: ignore[arg-type]


class LiveReader:
    """Call 8, blind to the expected answers, exactly as the product reads a sheet."""

    def __init__(self) -> None:
        from ai.client import CallContext

        self.ctx = CallContext(mode="live")

    def read(self, jpeg: bytes, form: Form) -> ReadOut | None:
        from ai.calls.c08_answer_reading import read_sheet

        out = read_sheet(base64.b64encode(jpeg).decode(), "image/jpeg", form, context=self.ctx)
        if out is None:
            return None
        return ReadOut(
            [c.text for c in out.cells],
            [c.confidence for c in out.cells],
            [c.status for c in out.cells],
            sum(r.cost_usd for r in out.runs),
        )


# --- tidy ---------------------------------------------------------------------------------------


def _gray(img: Image.Image, width: int = 200) -> np.ndarray:
    g = img.convert("L")
    g = g.resize((width, max(1, round(g.height * width / g.width))))
    return np.asarray(g, dtype=np.float32)


def dhash(img: Image.Image) -> int:
    g = np.asarray(img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def sharpness(img: Image.Image) -> float:
    g = _gray(img, 600)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def quality(img: Image.Image) -> float:
    """Sharper and better lit is better: sharpness, penalised by distance from a mid-bright page."""
    g = _gray(img, 300)
    return sharpness(img) * max(0.05, 1 - abs(float(g.mean()) - 170) / 170)


def fix_rotation(img: Image.Image) -> tuple[Image.Image, bool]:
    """EXIF first, then a quarter turn if the page lies on its side. Returns (image, uncertain).

    A sheet is a portrait page. A landscape photo is turned a quarter; an upside-down page is
    guessed from where the ink sits (the header is heavier than the foot) and reported as
    uncertain when the two ends are close, so a person checks the sheet.
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    turned = img.width > img.height
    if turned:
        img = img.rotate(90, expand=True)
    g = _gray(img, 200)
    ink = (g < g.mean() * 0.7).sum(axis=1).astype(np.float64)
    third = max(1, len(ink) // 3)
    top, bottom = float(ink[:third].sum()), float(ink[-third:].sum())
    close = abs(top - bottom) <= 0.2 * max(top, bottom, 1.0)
    if not close and bottom > top:
        img = img.rotate(180)
    return img, close and turned


def shrink(img: Image.Image) -> Image.Image:
    long_edge = max(img.size)
    if long_edge <= LONG_EDGE:
        return img
    scale = LONG_EDGE / long_edge
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def to_jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


def black_out(img: Image.Image, boxes: tuple[Box, ...]) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    for x0, y0, x1, y1 in boxes:
        d.rectangle(
            (x0 * out.width, y0 * out.height, x1 * out.width, y1 * out.height), fill=(0, 0, 0)
        )
    return out


# --- the ingest ---------------------------------------------------------------------------------


@dataclass
class Cand:
    path: Path
    sha: str
    img: Image.Image
    phash: int
    q: float
    label: tuple[str, int] | None
    uncertain_rotation: bool
    scan: Scan | None = None


@dataclass
class Report:
    files_in: int = 0
    dropped: list[str] = field(default_factory=list)
    possible_dups: list[str] = field(default_factory=list)
    unlabelled: list[str] = field(default_factory=list)
    out_of_range: list[str] = field(default_factory=list)
    rotation_check: list[str] = field(default_factory=list)
    names_found: list[str] = field(default_factory=list)
    names_not_scanned: list[str] = field(default_factory=list)
    name_regions: int = 0
    unread: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    disagreements: int = 0
    boxes_compared: int = 0
    ai_cost_usd: float = 0.0
    sheets_per_class: dict[str, int] = field(default_factory=dict)
    no_sheet: dict[str, list[int]] = field(default_factory=dict)
    dictation_words: dict[tuple[str, int], tuple[str | None, str | None]] = field(
        default_factory=dict
    )
    words_read: int = 0


def label_from_name(name: str) -> tuple[str, int] | None:
    m = NAME_RE.search(Path(name).stem)
    return (m["cls"].upper(), int(m["roll"])) if m else None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def read_truth(folder: Path, klass: PilotClass, form: Form) -> dict[int, list[str]]:
    """truth/{class}.csv: roll, q1..qN (digits; empty is a blank box)."""
    path = folder / "truth" / f"{klass.class_code}.csv"
    if not path.is_file():
        return {}
    out: dict[int, list[str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            roll = int(str(row["roll"]).strip())
            cells = [(row.get(f"q{i}") or "").strip() for i in range(1, len(form.items) + 1)]
            if (row.get("q1") or "").strip().upper() == "ABSENT":
                continue  # the child was absent: the manifest lists the roll under absent
            if any(c and not c.isdigit() for c in cells):
                raise ValueError(f"{path.name}: roll {roll} has a box that is not digits")
            out[roll] = cells
    return out


def scan_cached(scanner: Scanner, c: Cand, cache: dict[str, Any]) -> Scan | None:
    key = "v2:" + hashlib.sha256(to_jpeg(c.img)).hexdigest()  # v2: the scan also copies words
    hit = cache.get("scan", {}).get(key)
    if hit is not None:
        boxes = tuple((b[0], b[1], b[2], b[3]) for b in hit["boxes"])
        w = hit.get("words") or [None, None]
        return Scan(hit["class_code"], hit["roll"], hit["name_present"], boxes, (w[0], w[1]))
    out = None
    for _ in range(3):  # a scan can fail for a passing reason (timeout, busy): try again
        out = scanner.scan(to_jpeg(c.img))
        if out is not None:
            break
    if out is not None:
        cache.setdefault("scan", {})[key] = {
            "class_code": out.class_code,
            "roll": out.roll,
            "name_present": out.name_present,
            "boxes": [list(b) for b in out.name_boxes],
            "words": list(out.words),
        }
    return out


def collect(raw: Path, scanner: Scanner | None, cache: dict[str, Any], rep: Report) -> list[Cand]:
    cands: list[Cand] = []
    seen: dict[str, Path] = {}
    for path in sorted(p for p in raw.rglob("*") if p.suffix.lower() in SUFFIXES):
        rep.files_in += 1
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen:
            rep.dropped.append(f"{path.name} (identical to {seen[sha].name})")
            continue
        seen[sha] = path
        img, uncertain = fix_rotation(Image.open(io.BytesIO(data)))
        img = shrink(img)
        label = label_from_name(path.name)
        c = Cand(path, sha, img, dhash(img), quality(img), label, uncertain)
        if label is None and scanner is not None:
            c.scan = scan_cached(scanner, c, cache)
            if c.scan and c.scan.class_code and c.scan.roll:
                c.label = (c.scan.class_code.upper(), c.scan.roll)
        if uncertain:
            rep.rotation_check.append(path.name)
        cands.append(c)
    return cands


def choose(cands: list[Cand], manifest: Manifest, rep: Report) -> dict[tuple[str, int], Cand]:
    groups: dict[tuple[str, int], list[Cand]] = {}
    for c in cands:
        if c.label is None:
            rep.unlabelled.append(c.path.name)
            continue
        klass = manifest.klass(c.label[0])
        if klass is None or not 1 <= c.label[1] <= klass.strength:
            rep.out_of_range.append(f"{c.path.name} ({c.label[0]} roll {c.label[1]})")
            continue
        groups.setdefault(c.label, []).append(c)
    best: dict[tuple[str, int], Cand] = {}
    for key, items in groups.items():
        items.sort(key=lambda c: c.q, reverse=True)
        best[key] = items[0]
        for other in items[1:]:
            near = hamming(other.phash, items[0].phash) <= NEAR_BITS
            kind = "near-duplicate" if near else "another photo"
            rep.dropped.append(f"{other.path.name} ({kind} of {items[0].path.name}; kept sharper)")
    for c in cands:  # an unlabelled photo that looks like a kept one is flagged, never dropped
        if c.label is None:
            for key, kept in best.items():
                if hamming(c.phash, kept.phash) < NEAR_BITS:
                    rep.possible_dups.append(f"{c.path.name} may repeat {key[0]}-roll{key[1]:02d}")
                    break
    return best


def normalise(
    best: dict[tuple[str, int], Cand],
    out: Path,
    scanner: Scanner | None,
    cache: dict[str, Any],
    rep: Report,
) -> dict[tuple[str, int], tuple[str, bytes]]:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    result: dict[tuple[str, int], tuple[str, bytes]] = {}
    for (cls, roll), c in sorted(best.items()):
        name = f"{cls}-roll{roll:02d}.jpg"
        scan = c.scan or (scan_cached(scanner, c, cache) if scanner is not None else None)
        img = c.img
        if scan is not None and any(scan.words):
            rep.dictation_words[(cls, roll)] = scan.words
        if scan is None:
            rep.names_not_scanned.append(name)
        elif scan.name_present:
            img = black_out(img, scan.name_boxes)
            rep.names_found.append(f"{name} ({len(scan.name_boxes)} region(s))")
            rep.name_regions += len(scan.name_boxes)
        jpeg = to_jpeg(img)
        (out / name).write_bytes(jpeg)
        result[(cls, roll)] = (name, jpeg)
    return result


def read_cached(
    reader: Reader, jpeg: bytes, form: Form, cache: dict[str, Any], rep: Report, max_usd: float
) -> ReadOut | None:
    dictated = [i.a for i in form.items if i.n <= 2]
    key = f"{hashlib.sha256(jpeg).hexdigest()}:{len(form.items)}:{dictated}"
    hit = cache.get("reads", {}).get(key)
    if hit is not None:
        return ReadOut(hit["texts"], hit["confidences"], hit["statuses"], 0.0)
    if rep.ai_cost_usd >= max_usd:
        return None
    out = reader.read(jpeg, form)
    if out is None:
        return None
    rep.ai_cost_usd += out.cost_usd
    cache.setdefault("reads", {})[key] = {
        "texts": out.texts,
        "confidences": out.confidences,
        "statuses": out.statuses,
    }
    return out


def fill_dictation(
    read: ReadOut, words: tuple[str | None, str | None] | None, rep: Report
) -> ReadOut:
    """A child who wrote a dictated number in words: turn the words into digits, by code. The box
    stays marked "check", so a person looks at it. Only an empty digit read is replaced."""
    if not words:
        return read
    texts, conf, status = list(read.texts), list(read.confidences), list(read.statuses)
    for i, w in enumerate(words):
        if w and not texts[i]:
            n = numwords.parse(w)
            if n is not None:
                texts[i], conf[i], status[i] = str(n), 0.7, "check"
                rep.words_read += 1
    return ReadOut(texts, conf, status, read.cost_usd)


def compare(read: ReadOut, truth: list[str], acc: Counter[str], rep: Report) -> None:
    wrong_here = 0
    for text, conf, status, want in zip(
        read.texts, read.confidences, read.statuses, truth, strict=True
    ):
        bad = text != want
        acc["boxes"] += 1
        acc["right"] += not bad
        bucket = "hi" if conf >= ans.CONFIDENCE_BAR else "lo"
        acc[f"{bucket}_n"] += 1
        acc[f"{bucket}_wrong"] += bad
        if status == "ok":
            acc["auto_n"] += 1
            acc["auto_wrong"] += bad
        wrong_here += bad
    acc["sheets"] += 1
    acc["sheets_wrong"] += wrong_here > 0
    rep.boxes_compared += len(truth)
    rep.disagreements += wrong_here


def build(
    folder: Path,
    *,
    manifest: Manifest | None = None,
    scanner: Scanner | None = None,
    reader: Reader | None = None,
    max_usd: float = 3.0,
    accuracy_path: Path | None = None,
) -> Report:
    manifest = manifest or load_manifest(folder / "manifest.yaml")
    rep = Report()
    cache_path = folder / ".cache" / "ingest.json"
    cache = _load_json(cache_path)
    cands = collect(folder / "raw", scanner, cache, rep)
    best = choose(cands, manifest, rep)
    files = normalise(best, folder / "sheets", scanner, cache, rep)

    classes_out = []
    accuracy: dict[str, Counter[str]] = {}
    for klass in manifest.classes:
        form = form_for(klass)
        read_form = read_form_for(klass, manifest.test)
        truth = read_truth(folder, klass, read_form)
        sheets: list[ans.Sheet] = []
        acc = accuracy.setdefault(klass.class_code, Counter())
        for roll in range(1, klass.strength + 1):
            name, jpeg = files.get((klass.class_code, roll), (None, b""))
            tag = f"{klass.class_code}-roll{roll:02d}"
            if roll in klass.absent:
                sheets.append(ans.Sheet(roll=roll, file=None, status="absent"))
                continue
            ai_read: ReadOut | None = None
            if name is not None and reader is not None:
                ai_read = read_cached(reader, jpeg, read_form, cache, rep, max_usd)
                if ai_read is not None:
                    ai_read = fill_dictation(
                        ai_read, rep.dictation_words.get((klass.class_code, roll)), rep
                    )
            given: list[str] | None = None
            conf: list[float] = []
            source: str | None = None
            if roll in truth:
                given, conf, source = truth[roll], [1.0] * len(read_form.items), "truth"
            if ai_read is not None:
                if given is not None:
                    source = "truth+ai"
                    compare(ai_read, truth[roll], acc, rep)
                else:
                    given, conf, source = ai_read.texts, ai_read.confidences, "ai"
            if given is None:
                if name is None:
                    sheets.append(ans.Sheet(roll=roll, file=None, status="no_sheet"))
                else:
                    rep.unread.append(name)
                    digest = hashlib.sha256(jpeg).hexdigest()
                    sheets.append(
                        ans.Sheet(roll=roll, file=name, status="no_sheet", image_hash=digest)
                    )
                continue
            marked = ans.mark_answers(read_form, given, conf, [None] * len(given))
            verified = source in ("truth", "truth+ai")
            sheets.append(
                ans.Sheet(
                    roll=roll,
                    file=name,
                    status="entered",
                    source=source,  # type: ignore[arg-type]
                    verified=verified,
                    image_hash=hashlib.sha256(jpeg).hexdigest() if name else None,
                    answers=marked,
                    summary=ans.summarise(form, marked),
                )
            )
            if not verified:
                rep.unverified.append(tag)
            if any(a.confidence < ans.CONFIDENCE_BAR for a in marked):
                rep.low_confidence.append(tag)
        rep.sheets_per_class[klass.class_code] = sum(1 for s in sheets if s.status == "entered")
        rep.no_sheet[klass.class_code] = [s.roll for s in sheets if s.status == "no_sheet"]
        classes_out.append(ans.class_out(klass, sheets, form))

    test = ans.build_test(
        manifest.classes,
        manifest.test,
        manifest.test.name,
        manifest.test.date.isoformat() if manifest.test.date else None,
        manifest.test.paper_version,
    )
    doc = ans.AnswerFile(test=test, classes=classes_out)
    (folder / "pilot_answers.json").write_text(doc.model_dump_json(indent=1), encoding="utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    (folder / "ingest_report.md").write_text(render_report(rep), encoding="utf-8")
    if accuracy_path is not None and any(a["boxes"] for a in accuracy.values()):
        accuracy_path.parent.mkdir(parents=True, exist_ok=True)
        accuracy_path.write_text(render_accuracy(accuracy), encoding="utf-8")
    return rep


# --- reports (counts only in anything tracked) ----------------------------------------------------


def render_report(r: Report) -> str:
    def block(title: str, items: list[str]) -> str:
        return f"\n## {title} ({len(items)})\n" + ("".join(f"- {i}\n" for i in items) or "- none\n")

    head = (
        "# Pilot ingest report\n\nLocal file with file names and roll numbers. Do not commit.\n\n"
        f"- Files in: {r.files_in}\n- Sheets per class: {r.sheets_per_class}\n"
        f"- Name regions blacked out: {r.name_regions}\n"
        f"- Dictation boxes written in words and read into digits (check them): {r.words_read}\n"
        f"- Boxes compared with hand-keyed truth: {r.boxes_compared}, "
        f"disagreements: {r.disagreements}\n- AI cost this run: USD {r.ai_cost_usd:.4f}\n"
    )
    return (
        head
        + block("Dropped files", r.dropped)
        + block("Possible duplicates (kept, please check)", r.possible_dups)
        + block("No class or roll could be read: review", r.unlabelled)
        + block("Class or roll out of range: review", r.out_of_range)
        + block("Orientation guessed: review", r.rotation_check)
        + block("Sheets where a name was found: HUMAN REVIEW", r.names_found)
        + block("Sheets with the name scan not run: HUMAN REVIEW", r.names_not_scanned)
        + block("Rolls with no sheet", [f"{k}: {v}" for k, v in r.no_sheet.items()])
        + block("Sheets with a low-confidence box", r.low_confidence)
        + block("Sheets not read", r.unread)
        + block("Sheets unverified (no hand-keyed truth)", r.unverified)
    )


def _row(code: str, a: Counter[str]) -> str:
    return (
        f"| {code} | {a['right']} of {a['boxes']} | {a['sheets_wrong']} of {a['sheets']} | "
        f"{a['auto_wrong']} of {a['auto_n']} | {a['hi_wrong']} of {a['hi_n']} | "
        f"{a['lo_wrong']} of {a['lo_n']} |"
    )


def render_accuracy(acc: dict[str, Counter[str]]) -> str:
    total: Counter[str] = Counter()
    for a in acc.values():
        total.update(a)
    lines = [
        "# Pilot reading accuracy (call 8 on real pilot sheets)",
        "",
        "Generated by `python tasks.py pilot-ingest` from hand-keyed truth. Counts only, "
        "no per-child rows.",
        f"Confidence note: from {total['sheets']} sheets ({total['boxes']} boxes); "
        "read as directional.",
        "",
        "| Class | Boxes read right | Sheets with a wrong read | Auto-accepted reads wrong | "
        "Confidence 0.8 or more: wrong | Confidence below 0.8: wrong |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [_row(code, a) for code, a in sorted(acc.items()) if a["boxes"]]
    lines += [_row("All", total), ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--folder", default=str(ROOT / "data" / "pilot"))
    ap.add_argument(
        "--no-ai", action="store_true", help="file names and truth only; no model calls"
    )
    ap.add_argument("--max-usd", type=float, default=3.0)
    args = ap.parse_args(argv)
    folder = Path(args.folder)
    if not (folder / "manifest.yaml").is_file():
        print(f"No manifest.yaml in {folder}. See docs/pilot/PILOT-DEMO.md.")
        return 1
    scanner: Scanner | None = None
    reader: Reader | None = None
    if not args.no_ai:
        from ai import config

        config.load_env()
        print(f"AI steps on: call 15 (header, names) and call 8 (reading), cap USD {args.max_usd}.")
        scanner, reader = LiveScanner(), LiveReader()
    rep = build(
        folder,
        scanner=scanner,
        reader=reader,
        max_usd=args.max_usd,
        accuracy_path=ROOT / "docs" / "evidence" / "pilot_reading_accuracy.md",
    )
    print(render_report(rep).split("\n## ")[0])
    print(f"Full report: {folder / 'ingest_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
