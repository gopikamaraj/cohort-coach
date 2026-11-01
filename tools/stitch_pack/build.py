"""Builds the Stitch pack from the capture files: long images, annotated copies, contact sheets, a spec
and a ready-to-paste Stitch prompt per screen, the tokens file, the index and the README.

Reads the JSON the capture tool wrote beside each image. Never draws on a clean image.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs" / "design" / "stitch" / "pack"
DESIGN = ROOT / "docs" / "design" / "stitch" / "DESIGN.md"
MAX_PART = 2400  # device pixels
PART_OVERLAP = 8
MAX_BYTES = 4 * 1024 * 1024
BOX = (216, 27, 96)  # magenta: contrasts with the teal and white of the app
PROMPT_MAX = 1800

# What a control does, by data-testid, for the element tables. Anything not here is described from its
# role and label.
TESTID_DOES: dict[str, str] = {
    "brand": "Goes to the role picker (the landing page).",
    "assistant-open": "Opens the assistant drawer, scoped to the user's role.",
    "status": "Shows whether the app is online and the measured connection speed.",
    "check-change": "Changes which check (kind, date, form) the papers belong to.",
    "check-count": "Shows how many papers are entered out of the expected number.",
    "finish": "Finishes the check and works out the class's errors on this phone.",
    "next-child": "Saves this child's answers and moves to the next roll number.",
    "child-select": "Chooses which child's sheet to enter.",
    "absent": "Marks the roll number absent so it is skipped.",
    "sample-sheet": "Shows a sample answer sheet.",
    "photo-input": "Picks a photo of the answer sheet; the answers are read and the photo is not kept.",
    "paper-details": "Opens the panel for printing a paper for this check.",
    "paper-make": "Makes the paper by code from the approved rules.",
    "home-action": "The one next action for her term.",
    "home-practice": "Opens the Practice Class.",
    "home-programme": "Opens My programme.",
    "home-history": "Opens What I entered.",
    "home-profile": "Opens My profile.",
    "load-demo": "Loads the simulated class into this phone.",
    "advance": "Moves the demo to term 2.",
    "offline-toggle": "Pretends the phone is offline to show what still works.",
    "reset": "Clears the demo data.",
    "start-practice": "Starts a rehearsal with five simulated children.",
    "send": "Sends what she typed to the simulated class.",
    "end": "Ends the rehearsal and asks for feedback.",
    "use-voice": "Switches to speaking her turn.",
    "use-text": "Switches to typing her turn.",
    "history-toggle": "Shows or hides the answers entered.",
    "demo-next": "Goes to the next demo step, as the right role.",
    "demo-back": "Goes to the previous demo step.",
    "demo-reset": "Resets the demo: clears this session's server rows and this phone's demo class.",
    "demo-guide": "Opens the judge guide's question for this step.",
    "demo-begin": "Starts the demo as a teacher.",
    "demo-make-sheets": "Makes 20 synthetic sheets for class 3A.",
    "demo-zip": "Downloads the sheets as one zip.",
    "demo-use-1": "Sends sheet 1 to the AI reader.",
    "demo-autofill": "Loads the other sheets from the demo answer file with no AI call.",
    "demo-approve": "Approves this sheet's read and opens the next to review.",
    "demo-finish": "Submits the check.",
    "demo-simulate": "Simulates the other 24 classes and forms cohorts with the real rules.",
    "demo-audio": "Makes lesson 1 (pre-approved for the demo) and plays it.",
    "demo-chat-ask": "Sends the question to the cohort chat.",
    "demo-chat-skip": "Stops waiting for a person and checks whether the AI may answer.",
    "demo-post": "Simulates the post-test on the twin paper.",
}

NAV_DOES = {
    "Home": "Goes to Home.",
    "Enter check": "Goes to the check entry.",
    "My class": "Goes to What my class gets wrong.",
    "Practice": "Goes to the Practice Class.",
    "More": "Opens the menu of the other screens.",
}


def font(size: int, bold: bool = True) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def save(im: Image.Image, path: Path) -> None:
    """PNG, shrunk by palette only if it would pass 4 MB."""
    im.save(path, optimize=True)
    if path.stat().st_size > MAX_BYTES:
        im.convert("P", palette=Image.Palette.ADAPTIVE, colors=128).save(path, optimize=True)


def metas(dirs: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    out = []
    for d in dirs:
        for f in sorted(d.glob("*.json")):
            if f.name.endswith(("-elements.json",)) or f.name == "capture-index.json":
                continue
            m = json.loads(f.read_text(encoding="utf-8"))
            if "viewportFile" in m:
                out.append((d, m))
    return out


def visible_in_viewport(
    e: dict[str, Any], m: dict[str, Any]
) -> tuple[float, float, float, float] | None:
    c = m["container"]
    if e["inContainer"]:
        x, y, w, h = e["page"]["x"], e["page"]["y"], e["page"]["w"], e["page"]["h"]
        if y >= c["bottom"] or y + h <= c["top"]:
            return None
    else:
        r = e["rect"]
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        if y >= m["vh"] or y + h <= 0:
            return None
    return x, y, w, h


def draw_boxes(
    im: Image.Image, boxes: list[tuple[str, tuple[float, float, float, float]]], dpr: float
) -> Image.Image:
    out = im.convert("RGB").copy()
    d = ImageDraw.Draw(out, "RGBA")
    f = font(max(18, int(11 * dpr)))
    for label, (x, y, w, h) in boxes:
        x0, y0, x1, y1 = x * dpr, y * dpr, (x + w) * dpr, (y + h) * dpr
        d.rectangle(
            [x0, y0, x1, y1], outline=BOX + (255,), width=max(2, int(1.5 * dpr)), fill=BOX + (28,)
        )
        tw = d.textlength(label, font=f)
        th = f.size + 6 if hasattr(f, "size") else 20
        tx = min(max(x0, 0), im.width - tw - 8)
        ty = max(y0 - th, 0)
        d.rectangle([tx, ty, tx + tw + 8, ty + th], fill=BOX + (255,))
        d.text((tx + 4, ty + 2), label, fill=(255, 255, 255), font=f)
    return out


def split_parts(im: Image.Image) -> list[Image.Image]:
    if im.height <= MAX_PART:
        return [im]
    parts, y = [], 0
    while y < im.height:
        end = min(y + MAX_PART, im.height)
        parts.append(im.crop((0, y, im.width, end)))
        if end >= im.height:
            break
        y = end - PART_OVERLAP
    return parts


def build_long(d: Path, m: dict[str, Any]) -> Image.Image | None:
    if not m["slices"]:
        return None
    dpr = m["dpr"]
    c = m["container"]
    first = Image.open(d / m["slices"][0]["file"]).convert("RGB")
    last = Image.open(d / m["slices"][-1]["file"]).convert("RGB")
    w = first.width
    top = int(round(c["top"] * dpr))
    bottom = int(round(c["bottom"] * dpr))
    total = int(round((c["top"] + c["scrollHeight"] + (m["vh"] - c["bottom"])) * dpr))
    canvas = Image.new("RGB", (w, total), (255, 255, 255))
    canvas.paste(first.crop((0, 0, w, top)), (0, 0))
    for s in m["slices"]:
        im = Image.open(d / s["file"]).convert("RGB")
        canvas.paste(
            im.crop((0, top, w, bottom)), (0, int(round((c["top"] + s["scrollTop"]) * dpr)))
        )
    tail = last.crop((0, bottom, w, last.height))
    canvas.paste(tail, (0, int(round((c["top"] + c["scrollHeight"]) * dpr))))
    return canvas


def process(d: Path, m: dict[str, Any]) -> dict[str, Any]:
    base = m["base"]
    dpr = m["dpr"]
    files: dict[str, Any] = {
        "viewport": m["viewportFile"],
        "slices": [s["file"] for s in m["slices"]],
        "hscroll": m.get("hscroll"),
    }
    # annotated viewport
    boxes = []
    for e in m["elements"]:
        v = visible_in_viewport(e, m)
        if v:
            boxes.append((e["id"], v))
    clean = Image.open(d / m["viewportFile"])
    ann = draw_boxes(clean, boxes, dpr)
    save(ann, d / f"{base}-annotated.png")
    files["annotated"] = f"{base}-annotated.png"
    files["on_viewport"] = [b[0] for b in boxes]
    # long image
    long_im = build_long(d, m)
    files["long"], files["long_annotated"] = [], []
    if long_im is not None:
        parts = split_parts(long_im)
        for i, p in enumerate(parts, 1):
            name = f"{base}-long.png" if len(parts) == 1 else f"{base}-long-p{i}.png"
            save(p, d / name)
            files["long"].append(name)
        lboxes = [
            (e["id"], (e["page"]["x"], e["page"]["y"], e["page"]["w"], e["page"]["h"]))
            for e in m["elements"]
        ]
        lann = draw_boxes(long_im, lboxes, dpr)
        parts = split_parts(lann)
        for i, p in enumerate(parts, 1):
            name = (
                f"{base}-long-annotated.png"
                if len(parts) == 1
                else f"{base}-long-annotated-p{i}.png"
            )
            save(p, d / name)
            files["long_annotated"].append(name)
        files["on_long"] = [b[0] for b in lboxes]
    else:
        files["on_long"] = files["on_viewport"]
    m["files"] = files
    (d / f"{base}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    return m


def contact_sheet(d: Path, screen_id: str, ms: list[dict[str, Any]]) -> str | None:
    if not ms:
        return None
    primary = (ms[0]["role"], ms[0]["lang"], ms[0]["viewport"])
    pick = [m for m in ms if (m["role"], m["lang"], m["viewport"]) == primary]
    pick += [m for m in ms if m not in pick]
    pick = pick[:4]
    n = len(pick)
    gap, label_h = 24, 56
    imgs = [(m, Image.open(d / m["viewportFile"]).convert("RGB")) for m in pick]
    # tiles of equal height, so a desktop and a phone view are both readable; shrink until the sheet fits 3,000 px
    target_h = 1500
    while True:
        sizes = [(int(im.width * target_h / im.height), target_h) for _, im in imgs]
        if gap * (n + 1) + sum(w for w, _ in sizes) <= 3000 or target_h <= 400:
            break
        target_h -= 50
    tiles = [
        (m, im.resize(sz, Image.Resampling.LANCZOS))
        for (m, im), sz in zip(imgs, sizes, strict=True)
    ]
    height = label_h + max(t.height for _, t in tiles) + gap * 2
    sheet = Image.new(
        "RGB", (gap * (n + 1) + sum(t.width for _, t in tiles), height), (238, 242, 242)
    )
    dr = ImageDraw.Draw(sheet)
    f = font(28)
    x = gap
    for m, t in tiles:
        dr.text(
            (x, 12),
            f"{m['state']} · {m['role']} · {m['lang']} · {m['viewport']}"[:60],
            fill=(25, 28, 28),
            font=f,
        )
        sheet.paste(t, (x, label_h + gap // 2))
        x += t.width + gap
    name = f"{screen_id}-sheet.png"
    save(sheet, d / name)
    return name


def does(e: dict[str, Any]) -> str:
    t = e["testid"]
    if t in TESTID_DOES:
        return TESTID_DOES[t]
    if e["region"] == "bottom bar" and e["name"] in NAV_DOES:
        return NAV_DOES[e["name"]]
    r = e["role"]
    if r == "link":
        h = e["href"]
        return f"Opens {h}." if h.startswith("#/") else "Opens a link."
    if r == "heading":
        return "Heading: names the section below it."
    if r in ("textbox", "combobox"):
        return (
            "Field: she types or chooses a value."
            if r == "textbox"
            else "Dropdown: she chooses one value."
        )
    if r == "checkbox":
        return "Tick box: turns an option on or off."
    if r == "radio":
        return "Choice: selects this option."
    if r == "button":
        return f"Button: tap to {e['name'].rstrip('.').lower()}." if e["name"] else "Button."
    if r == "image":
        return "Picture."
    if r == "label":
        return "Label for the field next to it."
    if r in ("status", "alert"):
        return "Message shown to the user (read out by a screen reader)."
    return "Shows text or a value."


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def steps_in_words(steps: list[dict[str, Any]]) -> str:
    out = []
    for s in steps:
        k, v = next(iter(s.items()))
        out.append(
            {
                "click": f"tap {v}",
                "clickText": f'tap "{v}"',
                "goto": f"go to {v}",
                "wait": f"wait for {v}",
                "fill": f"type into {v[0] if isinstance(v, list) else v}",
                "select": f"choose in {v[0] if isinstance(v, list) else v}",
            }.get(k, f"{k}: {v}")
        )
    return ", then ".join(out) if out else "open the route"


def findings(ms: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    small: dict[str, str] = {}
    sizes: dict[str, set[str]] = {}
    for m in ms:
        for e in m["elements"]:
            if (
                e["interactive"]
                and (e["rect"]["h"] < 43.5 or e["rect"]["w"] < 43.5)
                and e["role"] not in ("link",)
                and e["tag"] != "label"
            ):
                small[e["name"][:40] or e["testid"]] = (
                    f"{m['state']}/{m['lang']}: {round(e['rect']['w'])} x {round(e['rect']['h'])} px"
                )
            sizes.setdefault(f"{m['state']}|{m['lang']}|{m['viewport']}", set()).add(
                e["style"]["font"].split("/")[0].strip()
            )
        if m.get("hscroll"):
            out.append(
                f'A wide table or row scrolls sideways in state "{m["state"]}" ({m["viewport"]}): see the -hscroll image.'
            )
    for name, where in list(small.items())[:6]:
        out.append(f'Touch target under 44 px: "{name}" ({where}).')
    for k, s in sizes.items():
        if len(s) > 5:
            out.append(
                f"{len(s)} distinct font sizes among the numbered elements in {k.replace('|', ', ')}: {', '.join(sorted(s))}."
            )
            break
    for m in ms:
        for c in m.get("checks", []):
            if c["rule"] == "demo-label-missing":
                out.append(
                    f'No "Demo" or "Simulated" label is visible on this screen although it shows demo data (state "{m["state"]}"). Rule 6 in CLAUDE.md says simulated data is labelled wherever it is shown.'
                )
                return out
    return out or [
        "No measured problem found in the numbered elements. A designer should still review hierarchy and spacing by eye."
    ]


def stitch_prompt(screen: dict[str, Any], ms: list[dict[str, Any]], num: str) -> str:
    states = sorted({m["state"] for m in ms})
    primary = next((m for m in ms), None)
    keep_ids = []
    if primary:
        for e in primary["elements"]:
            if (
                e["id"] in primary["files"]["on_viewport"]
                and (e["interactive"] or e["role"] == "heading")
                and len(keep_ids) < 8
            ):
                keep_ids.append(f"{e['id']} {e['name'][:30]} ({does(e).rstrip('.')})")
    head = (
        "Redesign this screen of a teacher-support app for Indian primary school teachers. "
        "Attached: the clean screenshot, the annotated screenshot with numbered elements, and a contact sheet of its states. "
        f'Screen: "{screen["name"]}". '
        f"**Keep:** the content, the order of actions, and the purpose of every numbered element. "
        "**Improve:** hierarchy, spacing, type scale and consistency, using Material 3 with the Calm Institutional palette (teal primary). "
        f"**Design these states:** {', '.join(states)}. "
    )
    tail = "**Constraints:** phone first at 390 px, touch targets of at least 44 px, English, Hindi and Tamil text must fit without cutting, no new features."
    elems = "; ".join(keep_ids)
    while True:
        text = head + f"**Elements to keep, by number:** {elems}. " + tail if elems else head + tail
        if len(text) <= PROMPT_MAX or not keep_ids:
            break
        keep_ids.pop()
        elems = "; ".join(keep_ids)
    return text[:PROMPT_MAX]


def spec(
    screen: dict[str, Any], num: str, d: Path, ms: list[dict[str, Any]], sheet: str | None
) -> str:
    L: list[str] = []
    ad = L.append
    ad(f"# {num} · {screen['name']}\n")
    ad(
        "_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._\n"
    )
    ad("## 1. Screen\n")
    langs = sorted({m["lang"] for m in ms})
    roles = sorted({m["role"] for m in ms})
    ad(
        f"- **Route:** `#{screen['route']}`\n- **Roles shown:** {', '.join(roles)}\n- **Languages captured:** {', '.join(langs)}\n- **Inventory id:** {screen.get('inventory', '')}\n- **When a user sees it:** {screen['when']}\n- **What they are trying to do:** {screen['goal']}\n- **Source:** {screen['source']}"
    )
    if screen.get("data"):
        ad(
            "- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label."
        )
    ad("")
    ad("## 2. Images\n")
    ad("| File | What it shows | Viewport | Scroll | State |\n| --- | --- | --- | --- | --- |")
    for m in ms:
        f = m["files"]
        vp = f"{m['vw']} x {m['vh']} @{int(m['dpr'])}x"
        st = f"{m['state']} · {m['role']} · {m['lang']}"
        ad(f"| {f['viewport']} | First viewport, clean | {vp} | top | {st} |")
        ad(
            f"| {f['annotated']} | Same, with numbered boxes {', '.join(f['on_viewport'][:3])}… | {vp} | top | {st} |"
        )
        for s in m["slices"]:
            ad(
                f"| {s['file']} | Scroll slice (80 px overlap) | {vp} | {int(s['scrollTop'])} px | {st} |"
            )
        for n in f["long"]:
            ad(
                f"| {n} | Stitched long image (fixed header and bottom bar kept once) | {vp} | full page | {st} |"
            )
        for n in f["long_annotated"]:
            ad(f"| {n} | Long image with numbered boxes | {vp} | full page | {st} |")
        if f.get("hscroll"):
            ad(
                f"| {f['hscroll']} | A wide row or table scrolled to its end | {vp} | sideways | {st} |"
            )
    if sheet:
        ad(f"| {sheet} | Contact sheet of the main states | — | — | all |")
    ad("")
    ad("## 3. Layout\n")
    for m in ms[:1]:
        regions: dict[str, list[str]] = {}
        for e in m["elements"]:
            regions.setdefault(e["region"], []).append(e["id"])
        ad(
            f'Top to bottom in the first state ("{m["state"]}"), by region, with the numbered elements in each:\n'
        )
        order = [
            "header",
            "language strip",
            "demo bar",
            "main",
            "dialog",
            "drawer",
            "bottom bar",
            "side rail",
            "footer",
        ]
        for r in sorted(regions, key=lambda r: order.index(r) if r in order else 99):
            ids = regions[r]
            ad(f"- **{r}**: {ids[0]} to {ids[-1]} ({len(ids)} elements)")
        c = m["container"]
        if c["mode"] == "element":
            ad(
                f"- The page scrolls inside one container: {int(c['clientHeight'])} px visible of {int(c['scrollHeight'])} px (the header and bottom bar stay fixed)."
            )
        else:
            ad("- The page does not scroll inside a container.")
    ad("")
    ad("## 4. Elements\n")
    ad(
        "Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.\n"
    )
    for m in ms:
        ad(f'### State "{m["state"]}" · {m["role"]} · {m["lang"]} · {m["viewport"]}\n')
        ad(
            "| # | Type | Label or text | Region | Position and size | Style | What it does |\n| --- | --- | --- | --- | --- | --- | --- |"
        )
        for e in m["elements"]:
            st = e["style"]
            style = f"{st['font']}; {st['color']}; bg {st['background']}; radius {st['radius']}"
            pos = f"{e['pct']['x']}%, {e['pct']['y']}% · {round(e['rect']['w'])} x {round(e['rect']['h'])}"
            lab = e["name"][:70] + (f" [{e['state']}]" if e["state"] else "")
            ad(
                f"| {e['id']} | {e['role']} | {esc(lab)} | {e['region']} | {pos} | {esc(style)} | {esc(does(e))} |"
            )
        ad("")
    ad("## 5. Content and data\n")
    ad(f"{screen['behaviour']}\n")
    ad("The text on screen, copied exactly from the page in the first state:\n")
    body = ms[0]["text"]["body"].strip()
    ad("```text\n" + body[:2500] + ("\n…(shortened)" if len(body) > 2500 else "") + "\n```\n")
    ad(
        "Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.\n"
    )
    ad("## 6. States and transitions\n")
    for st in dict.fromkeys(m["state"] for m in ms):
        how = (
            steps_in_words((screen.get("states") or {}).get(st, []))
            if (screen.get("states") or {}).get(st) is not None
            else "open the route"
        )
        if screen.get("sequence"):
            how = "reached in the 12-step demo session, in order"
        ad(f"- **{st}**: {how}.")
    ad(
        "- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`)."
    )
    ad("")
    ad("## 7. What works and what to change\n")
    ad(
        "Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.\n"
    )
    for f in findings(ms):
        ad(f"- {f}")
    ad("")
    ad("## 8. Constraints\n")
    ad(
        "- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.\n- Touch targets at least 44 px, primary buttons 48 px.\n- English, Hindi and Tamil text must fit without cutting.\n- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.\n- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.\n- No new features: redesign what exists."
    )
    return "\n".join(L) + "\n"


def tokens() -> str:
    text = DESIGN.read_text(encoding="utf-8")
    keep = []
    for title in ("Colour tokens", "Shape and spacing", "Type", "Layout"):
        m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        if m:
            keep.append(f"## {title}\n{m.group(1).strip()}\n")
    return (
        "# Design tokens to attach once\n\nFrom `docs/design/stitch/DESIGN.md` (Calm Institutional Material; Material 3). The app has a light theme only; the dark column in DESIGN.md is derived and not shipped.\n\n"
        + "\n".join(keep)
    )


def main(only: list[str] | None = None) -> None:
    manifest = yaml.safe_load((PACK / "manifest.yaml").read_text(encoding="utf-8"))
    screens = manifest["screens"]
    index_rows = []
    for i, screen in enumerate(screens, 1):
        num = f"{i:02d}"
        if only and screen["id"] not in only:
            continue
        d = PACK / f"{num}-{screen['id']}"
        if not d.exists():
            continue
        pairs = metas([d])
        if not pairs:
            continue
        ms = [process(dd, m) for dd, m in pairs]
        ms.sort(key=lambda m: m["base"])
        sheet = contact_sheet(d, screen["id"], ms)
        (d / "spec.md").write_text(spec(screen, num, d, ms, sheet), encoding="utf-8")
        (d / "stitch-prompt.md").write_text(stitch_prompt(screen, ms, num) + "\n", encoding="utf-8")
        print(f"built {d.name}: {len(ms)} states")
    (PACK / "00-tokens.md").write_text(tokens(), encoding="utf-8")
    for i, screen in enumerate(screens, 1):
        d = PACK / f"{i:02d}-{screen['id']}"
        if not d.exists():
            continue
        ms = [m for _, m in metas([d])]
        files = sum(1 for _ in d.glob("*.png"))
        elems = sum(len(m["elements"]) for m in ms)
        index_rows.append(
            (
                f"{i:02d}",
                screen["name"],
                screen["route"],
                sorted({m["state"] for m in ms}),
                files,
                elems,
                d.name,
            )
        )
    idx = [
        "# Stitch pack: index\n",
        "| # | Screen | Route | States | Images | Elements described | Folder |\n| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for n, name, route, st, files, elems, folder in index_rows:
        idx.append(
            f"| {n} | {name} | `#{route}` | {', '.join(st)} | {files} | {elems} | [{folder}](./{folder}/spec.md) |"
        )
    idx.append(
        "\nAttach once: [00-tokens.md](./00-tokens.md). Excluded routes and why: see `excluded` in [manifest.yaml](./manifest.yaml)."
    )
    (PACK / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    (PACK / "README.md").write_text(README, encoding="utf-8")


README = """# Stitch pack: how to use it

The pack shows Stitch what the app looks like today (pictures) and what each part does (words). It was captured from the built app in judge mode on simulated demo data, with recorded AI answers and a stub voice. Nothing real or private is in it.

## What is in each screen folder

- **Clean images** (`...png`): the first viewport as a user sees it, scroll slices (`-s01`, `-s02`, with 80 px overlap), a stitched long image of the whole page (`-long`, split into `-long-p1`, `-long-p2` when taller than 2,400 px) and, for wide tables, `-hscroll`.
- **Annotated images** (`-annotated`, `-long-annotated`): the same pictures with numbered boxes E1, E2 and so on. The numbers match the element tables in `spec.md`. The clean images are never drawn on.
- **Contact sheet** (`<screen>-sheet.png`): up to four states side by side in one image, for tools that take only one image.
- **`spec.md`**: the screen, its images, layout, every numbered element (type, text, position, style, what it does), the text on screen, the states, measured problems and constraints.
- **`stitch-prompt.md`**: a prompt of at most 1,800 characters, ready to paste.
- **`*.json`**: the raw element data for each capture.

## Using it in Stitch

1. Attach `00-tokens.md` once.
2. For each screen, attach the clean image, the annotated image and the contact sheet, then paste `stitch-prompt.md`.
3. Check Stitch's current limits on the number and size of images and on the length of the prompt before you start. Use the contact sheet when only one image is allowed, and the long image when you want the whole page.

## Rebuilding

`python tasks.py stitch-pack` rebuilds everything, then runs the validator. `--only home,check` rebuilds some screens.

## What the pack does not cover

Core scope only: no dark theme (the app has none), no Tamil, no empty, loading, error or offline states, no pilot mode. See the report `docs/build/reports/STITCH-PACK.md`.
"""

if __name__ == "__main__":
    main()
