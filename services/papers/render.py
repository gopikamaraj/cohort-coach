"""The child's paper, the answer key and the layout map, rendered on the server with WeasyPrint.

A4 portrait, black and white. Every box is placed at a fixed position in millimetres by
`layout()`, and the same numbers become the HTML and the layout map, so the map always matches the
printed boxes (tests/papers/test_render.py samples pixels to prove it). The child's paper has a
large form letter, the check code, a roll number box and no name field, wide undivided answer
boxes, and corner marks on every page; it never says "Cohort Coach". Fonts are embedded: Noto Sans,
Noto Sans Devanagari and Noto Sans Tamil (services/papers/fonts, SIL Open Font License).

On Windows, WeasyPrint needs the GTK3 runtime's Pango; set WEASYPRINT_DLL_DIRECTORIES or install
it in the default folder (see _dll_dirs). Linux and the Docker image install Pango with apt.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services.papers.rules import LAYOUTS, RuleSet, layout_langs

FONT_DIR = Path(__file__).with_name("fonts")
PAGE_W, PAGE_H = 210.0, 297.0
LEFT, TOP, RIGHT, BOTTOM = 14.0, 14.0, 196.0, 283.0
WIDTH = RIGHT - LEFT
PX_TO_MM = 25.4 / 96
LAYOUT_LANGS = {layout: layout_langs(layout) for layout in LAYOUTS}
DIGITS_PT = 22
TEXT_PT = 12
SECTION_PT = 14


def _dll_dirs() -> None:
    if os.name != "nt" or os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        return
    for d in (
        r"C:\Program Files\GTK3-Runtime Win64\lib",
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\msys64\mingw64\bin",
    ):
        if Path(d, "libpango-1.0-0.dll").exists():
            os.environ["WEASYPRINT_DLL_DIRECTORIES"] = d
            return


def weasyprint_available() -> bool:
    _dll_dirs()
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


@dataclass
class Box:
    id: str
    kind: str  # answer | roll | form | code | text | mark | operand | label
    page: int
    x: float
    y: float
    w: float
    h: float
    text: str = ""
    css: str = ""

    def as_map(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "page": self.page,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "w": round(self.w, 2),
            "h": round(self.h, 2),
        }


@dataclass
class Layout:
    pages: int = 1
    boxes: list[Box] = field(default_factory=list)


def _text(rules: RuleSet, lang_layout: str, key: str) -> str:
    """The fixed wording for a key, one line per language of the layout (never translated here)."""
    return "\n".join(rules.pack(lang).strings[key] for lang in LAYOUT_LANGS[lang_layout])


def _marks(page: int) -> list[Box]:
    s = 5.0
    spots = {
        "tl": (6.0, 6.0),
        "tr": (PAGE_W - 6 - s, 6.0),
        "bl": (6.0, PAGE_H - 6 - s),
        "br": (PAGE_W - 6 - s, PAGE_H - 6 - s),
    }
    return [Box(f"mark-{k}-p{page}", "mark", page, x, y, s, s) for k, (x, y) in spots.items()]


def _header(paper: dict[str, Any], rules: RuleSet, lang: str, page: int) -> tuple[list[Box], float]:
    two = len(LAYOUT_LANGS[lang]) > 1
    boxes = [
        Box(f"form-p{page}", "form", page, LEFT, TOP, 22, 22, paper["form"]),
        Box(f"code-p{page}", "code", page, 40, TOP, 92, 9, paper["check_code"]),
        Box(
            f"roll-label-p{page}",
            "text",
            page,
            136,
            TOP,
            60,
            6 if not two else 9,
            _text(rules, lang, "paper.roll").replace("\n", " / "),
        ),
        Box(f"roll-p{page}", "roll", page, 136, TOP + (8 if not two else 11), 60, 15),
        Box(f"no-name-p{page}", "text", page, 40, 25, 92, 12, _text(rules, lang, "paper.no_name")),
    ]
    y = TOP + (8 if not two else 11) + 15 + 4
    if page == 1:
        instr = _text(rules, lang, "paper.own_way") + "\n" + _text(rules, lang, "paper.skip")
        h = 24.0 if two else 13.0
        boxes.append(Box("instructions", "text", page, LEFT, y, WIDTH, h, instr))
        y += h + 3
    return boxes, y


def layout(paper: dict[str, Any], rules: RuleSet, lang: str) -> Layout:
    """Place every box of the child's paper, in mm, page by page."""
    two = len(LAYOUT_LANGS[lang]) > 1
    out = Layout()
    page = 1
    head, y = _header(paper, rules, lang, page)
    out.boxes += _marks(page) + head
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for it in paper["items"]:
        if groups and groups[-1][0] == it["section"]:
            groups[-1][1].append(it)
        else:
            groups.append((it["section"], [it]))
    sec_h = 14.0 if two else 8.0

    def new_page() -> float:
        nonlocal page
        page += 1
        out.pages = page
        hb, top = _header(paper, rules, lang, page)
        out.boxes.extend(_marks(page) + hb)
        return top

    for g_i, (section, items) in enumerate(groups):
        per_row, cell_w, cell_h = (2, 88.0, 22.0) if section == "dictation" else (4, 42.0, 40.0)
        gap = (WIDTH - per_row * cell_w) / (per_row - 1)
        rows = [items[i : i + per_row] for i in range(0, len(items), per_row)]
        if y + sec_h + cell_h > BOTTOM:
            y = new_page()
        out.boxes.append(
            Box(
                f"sec-{g_i}",
                "text",
                page,
                LEFT,
                y,
                WIDTH,
                sec_h,
                _text(rules, lang, f"sec.{section}"),
                "section",
            )
        )
        y += sec_h + 1
        for r_i, row in enumerate(rows):
            if y + cell_h > BOTTOM:
                y = new_page()
                # the section goes on over the page: say again what to do
                out.boxes.append(
                    Box(
                        f"sec-{g_i}-{r_i}",
                        "text",
                        page,
                        LEFT,
                        y,
                        WIDTH,
                        sec_h,
                        _text(rules, lang, f"sec.{section}"),
                        "section",
                    )
                )
                y += sec_h + 1
            for c, it in enumerate(row):
                x = LEFT + c * (cell_w + gap)
                n = it["n"]
                if section == "dictation":
                    out.boxes.append(Box(f"label-{n}", "label", page, x, y + 5, 8, 8, f"{n}"))
                    out.boxes.append(Box(f"answer-{n}", "answer", page, x + 10, y, 74, 18))
                else:
                    sign = "+" if it["operation"] == "add" else "−"
                    out.boxes += [
                        Box(f"label-{n}", "label", page, x, y, 8, 8, f"{n}"),
                        Box(f"top-{n}", "operand", page, x + 10, y, 28, 9, str(it["a"])),
                        Box(
                            f"bottom-{n}",
                            "operand",
                            page,
                            x + 10,
                            y + 9.5,
                            28,
                            9.5,
                            f"{sign} {it['b']}",
                            "rule",
                        ),
                        Box(f"answer-{n}", "answer", page, x + 3, y + 22, 36, 16),
                    ]
            y += cell_h + 3
        y += 2
    return out


_CSS = """
@font-face { font-family: 'Noto Sans'; src: url('{fd}/NotoSans-Regular.ttf'); }
@font-face { font-family: 'Noto Sans'; font-weight: bold; src: url('{fd}/NotoSans-Bold.ttf'); }
@font-face { font-family: 'Noto Sans Devanagari'; src: url('{fd}/NotoSansDevanagari-Regular.ttf'); }
@font-face { font-family: 'Noto Sans Devanagari'; font-weight: bold;
  src: url('{fd}/NotoSansDevanagari-Bold.ttf'); }
@font-face { font-family: 'Noto Sans Tamil'; src: url('{fd}/NotoSansTamil-Regular.ttf'); }
@font-face { font-family: 'Noto Sans Tamil'; font-weight: bold;
  src: url('{fd}/NotoSansTamil-Bold.ttf'); }
@page { size: A4 portrait; margin: 0; }
html, body { margin: 0; padding: 0; color: #000; background: #fff; }
body { font-family: 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Tamil';
  font-size: {tp}pt; line-height: 1.3; }
.page { position: relative; width: 210mm; height: 297mm; overflow: hidden; break-after: page; }
.page:last-child { break-after: auto; }
.b { position: absolute; box-sizing: border-box; white-space: pre-line; }
.mark { background: #000; }
.form { border: 0.8mm solid #000; font-size: 44pt; font-weight: bold; text-align: center;
  line-height: 20mm; }
.code { font-size: 14pt; font-weight: bold; letter-spacing: 0.3pt; }
.roll, .answer { border: 0.6mm solid #000; }
.label { font-weight: bold; font-size: 13pt; border: 0.3mm solid #000; border-radius: 4mm;
  text-align: center; line-height: 7.4mm; }
.operand { font-size: {dp}pt; text-align: right; line-height: 1.15; letter-spacing: 3pt; }
.rule { border-bottom: 0.5mm solid #000; }
.section { font-size: {sp}pt; font-weight: bold; }
"""


def _css() -> str:
    return (
        _CSS.replace("{fd}", FONT_DIR.as_uri())
        .replace("{tp}", str(TEXT_PT))
        .replace("{dp}", str(DIGITS_PT))
        .replace("{sp}", str(SECTION_PT))
    )


def paper_html(paper: dict[str, Any], rules: RuleSet, lang: str) -> tuple[str, Layout]:
    lay = layout(paper, rules, lang)
    pages: list[list[str]] = [[] for _ in range(lay.pages)]
    for b in lay.boxes:
        cls = f"b {b.kind} {b.css}".strip()
        style = f"left:{b.x}mm;top:{b.y}mm;width:{b.w}mm;height:{b.h}mm"
        fit = ' data-fit="1"' if b.text else ""
        pages[b.page - 1].append(
            f'<div id="{b.id}" class="{cls}" style="{style}"{fit}>{html.escape(b.text)}</div>'
        )
    lang_attr = "hi" if lang == "hi" else "ta" if lang == "ta" else "en"
    body = "".join(f'<div class="page">{"".join(p)}</div>' for p in pages)
    doc = (
        f'<!doctype html><html lang="{lang_attr}"><head><meta charset="utf-8">'
        f"<style>{_css()}</style></head><body>{body}</body></html>"
    )
    return doc, lay


def _overflow(document: Any) -> list[dict[str, Any]]:
    """Text blocks whose lines need more room than their box has (measured by WeasyPrint)."""
    from weasyprint.formatting_structure import boxes as wb

    out: list[dict[str, Any]] = []
    for page in document.pages:
        for box in page._page_box.descendants():
            el = getattr(box, "element", None)
            if el is None or el.get("data-fit") != "1" or not isinstance(box, wb.BlockBox):
                continue
            top = box.content_box_y()
            lines = [c for c in box.children if isinstance(c, wb.LineBox)]
            used = max((ln.position_y + ln.margin_height() - top for ln in lines), default=0)
            right = box.content_box_x() + box.width
            widest = max(
                (ch.position_x + ch.margin_width() for ln in lines for ch in ln.children),
                default=right,
            )
            if used > box.height + 0.5:
                out.append(
                    {
                        "id": el.get("id"),
                        "need_mm": used * PX_TO_MM,
                        "have_mm": box.height * PX_TO_MM,
                    }
                )
            elif widest > right + 0.5:
                out.append(
                    {
                        "id": el.get("id"),
                        "need_mm": (widest - box.content_box_x()) * PX_TO_MM,
                        "have_mm": box.width * PX_TO_MM,
                    }
                )
    return out


def render_paper(paper: dict[str, Any], rules: RuleSet, lang: str) -> tuple[bytes, dict[str, Any]]:
    """(PDF bytes, layout map) for the child's paper in one layout: en, hi, ta or en_hi."""
    if lang not in LAYOUT_LANGS:
        raise ValueError(f"no layout {lang}")
    _dll_dirs()
    from weasyprint import HTML

    doc_html, lay = paper_html(paper, rules, lang)
    document = HTML(string=doc_html, base_url=str(FONT_DIR)).render()
    pdf = document.write_pdf()
    layout_map = {
        "paper_hash": paper["hash"],
        "check_code": paper["check_code"],
        "form": paper["form"],
        "layout": lang,
        "units": "mm",
        "page": {"w": PAGE_W, "h": PAGE_H},
        "pages": lay.pages,
        "boxes": [b.as_map() for b in lay.boxes if b.kind != "mark"],
        "marks": [b.as_map() for b in lay.boxes if b.kind == "mark"],
        "answer_boxes": {
            str(int(b.id.split("-")[1])): b.as_map() for b in lay.boxes if b.kind == "answer"
        },
        "overflow": _overflow(document),
    }
    return bytes(pdf), layout_map


# --- answer key ------------------------------------------------------------------------------

_KEY_CSS = """
@page { size: A4 portrait; margin: 16mm 14mm;
  @top-left { content: element(code); } }
.mark { position: fixed; width: 5mm; height: 5mm; background: #000; }
h1 { font-size: 16pt; margin: 0 0 2mm; }
p { margin: 0 0 2mm; }
table { width: 100%; border-collapse: collapse; font-size: 11pt; }
th, td { border: 0.3mm solid #000; padding: 1.4mm 2mm; text-align: left; vertical-align: top; }
th { font-weight: bold; }
.num { font-size: 13pt; font-weight: bold; }
"""


# Lines of the answer key for the teacher that are about the paper, not the rule set's wording.
# TODO-HUMAN(Shivani: hi, Gopi: ta): drafts by Claude Code, 31 Oct.
KEY_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "made": "Made by code, not AI, from paper rules version {v}. Plan: {plan}. Paper "
        "fingerprint {fp}: a key and a paper with the same fingerprint have the same questions.",
        "plan.baseline_10": "10 questions, the same skills as the pilot paper",
        "plan.standard_10_5": "10 fixed questions and 5 chosen for this class",
        "no_error.anchor": "No error is tracked here: this question shows whether the child "
        "can take away at all (no borrowing).",
        "no_error": "No error is tracked on this question.",
    },
    "hi": {
        "made": "कोड से बना, AI से नहीं, पेपर नियम संस्करण {v} से। योजना: {plan}। पेपर की "
        "पहचान {fp}: एक ही पहचान वाली कुंजी और पेपर में वही सवाल होते हैं।",
        "plan.baseline_10": "10 सवाल, पायलट पेपर वाले कौशल",
        "plan.standard_10_5": "10 तय सवाल और 5 इस कक्षा के लिए चुने गए",
        "no_error.anchor": "यहाँ कोई गलती नहीं गिनी जाती: यह सवाल दिखाता है कि बच्चा घटा "
        "पाता है या नहीं (बिना उधार)।",
        "no_error": "इस सवाल पर कोई गलती नहीं गिनी जाती।",
    },
    "ta": {
        "made": "குறியீட்டால் உருவானது, AI-ஆல் அல்ல, தாள் விதிப் பதிப்பு {v}-இலிருந்து. "
        "திட்டம்: {plan}. தாளின் அடையாளம் {fp}: ஒரே அடையாளம் உள்ள விடைக் குறிப்பிலும் "
        "தாளிலும் அதே கேள்விகள்.",
        "plan.baseline_10": "10 கேள்விகள், முன்னோட்டத் தாளின் அதே திறன்கள்",
        "plan.standard_10_5": "10 நிலையான கேள்விகளும் இந்த வகுப்புக்குத் தேர்ந்த 5-உம்",
        "no_error.anchor": "இங்கே எந்தப் பிழையும் கணக்கிடப்படுவதில்லை: குழந்தையால் கழிக்க "
        "முடிகிறதா என்பதை இந்தக் கேள்வி காட்டுகிறது (கடன் இல்லாமல்).",
        "no_error": "இந்தக் கேள்வியில் எந்தப் பிழையும் கணக்கிடப்படுவதில்லை.",
    },
}


def _key_text(lang: str, key: str, **params: object) -> str:
    """One key line in each language of the layout, joined with a line break."""
    out = []
    for code in LAYOUT_LANGS[lang]:
        table = KEY_TEXT.get(code, KEY_TEXT["en"])
        out.append(html.escape(table.get(key, KEY_TEXT["en"][key]).format(**params)))
    return "<br>".join(out)


def key_html(paper: dict[str, Any], rules: RuleSet, lang: str) -> str:
    t = lambda k: html.escape(_text(rules, lang, k)).replace("\n", "<br>")  # noqa: E731
    rows = []
    for it in paper["items"]:
        if it["operation"] == "dictate":
            q = f"{t('key.say')}: <span class='num'>{it['a']}</span>"
        else:
            sign = "+" if it["operation"] == "add" else "−"
            q = f"<span class='num'>{it['a']} {sign} {it['b']}</span>"
        wrong = "<br>".join(
            f"{code}: {', '.join(str(a) for a in answers)}"
            for code, answers in [*it["wrong"].items(), *it["untracked"].items()]
        ) or _key_text(lang, "no_error.anchor" if it["template"] == "sub-no-borrow" else "no_error")
        kind = t("key.anchor") if it["is_anchor"] else t("key.adaptive")
        rows.append(
            f"<tr><td class='num'>{it['n']}</td><td>{kind}</td><td>{q}</td>"
            f"<td class='num'>{it['correct']}</td><td>{wrong}</td></tr>"
        )
    made = "<br>".join(
        html.escape(
            KEY_TEXT.get(code, KEY_TEXT["en"])["made"].format(
                v=paper["rules_version"],
                plan=KEY_TEXT.get(code, KEY_TEXT["en"]).get(
                    f"plan.{paper['blueprint']}", paper["blueprint"]
                ),
                fp=paper["hash"][:8],
            )
        )
        for code in LAYOUT_LANGS[lang]
    )
    not_assessed = ""
    if paper["not_assessed"]:
        not_assessed = f"<p>{t('key.not_assessed')}: {', '.join(paper['not_assessed'])}</p>"
    marks = (
        "<div class='mark' style='left:-8mm;top:-10mm'></div>"
        "<div class='mark' style='right:-8mm;top:-10mm'></div>"
        "<div class='mark' style='left:-8mm;bottom:-10mm'></div>"
        "<div class='mark' style='right:-8mm;bottom:-10mm'></div>"
    )
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><style>{_css()}{_KEY_CSS}"
        "</style></head><body style='font-size:11pt'>"
        f"{marks}<h1>{t('key.title')}</h1>"
        f"<p class='num'>{html.escape(paper['check_code'])}</p>"
        f"<p>{made}</p>{not_assessed}"
        f"<table><thead><tr><th>{t('key.item')}</th><th></th><th>{t('key.question')}</th>"
        f"<th>{t('key.correct')}</th><th>{t('key.wrong')}</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></body></html>"
    )


def render_key(paper: dict[str, Any], rules: RuleSet, lang: str) -> bytes:
    _dll_dirs()
    from weasyprint import HTML

    return bytes(HTML(string=key_html(paper, rules, lang), base_url=str(FONT_DIR)).write_pdf())
