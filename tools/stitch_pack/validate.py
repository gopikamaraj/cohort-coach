"""Validates the Stitch pack: every manifest entry has its files, the numbers on the annotated images
match the element tables, no image is blank or over 4 MB, long pages have slices and a stitched image,
Demo labels are present, prompts are short enough, and no file holds a secret or personal data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs" / "design" / "stitch" / "pack"
ROUTER = ROOT / "apps" / "pwa" / "src" / "lib" / "router.ts"
MAX_BYTES = 4 * 1024 * 1024
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|Api-Subscription-Key\s*[:=]\s*\S+|[\w.+-]+@[\w-]+\.[A-Za-z]{2,}|(?<![\d.])\d{10}(?![\d.]))"
)
SAFE_EMAILS = ("@types/", "@example")


def main() -> list[str]:
    fails: list[str] = []
    manifest = yaml.safe_load((PACK / "manifest.yaml").read_text(encoding="utf-8"))
    screens = manifest["screens"]

    # every route is in the manifest or excluded with a reason
    routes = re.findall(
        r'"(/[a-z]+)"',
        ROUTER.read_text(encoding="utf-8").split("export const ROUTES")[1].split("]")[0],
    )
    known = {s["route"].split("?")[0] for s in screens} | set(manifest.get("excluded", {}))
    for r in routes:
        if r not in known:
            fails.append(f"route {r} is neither in the manifest nor excluded")

    n_states = n_images = n_elems = 0
    for i, s in enumerate(screens, 1):
        d = PACK / f"{i:02d}-{s['id']}"
        if not d.exists():
            fails.append(f"{d.name}: folder missing")
            continue
        for f in ("spec.md", "stitch-prompt.md", f"{s['id']}-sheet.png"):
            if not (d / f).exists():
                fails.append(f"{d.name}/{f} missing")
        prompt = d / "stitch-prompt.md"
        if prompt.exists() and len(prompt.read_text(encoding="utf-8").strip()) > 1800:
            fails.append(f"{d.name}/stitch-prompt.md is longer than 1,800 characters")
        spec = (d / "spec.md").read_text(encoding="utf-8") if (d / "spec.md").exists() else ""
        want = [
            (v["role"], v["lang"], v["viewport"], st) for v in s["variants"] for st in v["states"]
        ]
        metas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))]
        have = {
            (m["role"], m["lang"], m["viewport"], m["state"]) for m in metas if "viewportFile" in m
        }
        for w in want:
            if w not in have:
                fails.append(f"{d.name}: missing capture {w}")
        for m in metas:
            if "viewportFile" not in m:
                continue
            n_states += 1
            files = m.get("files")
            if not files:
                fails.append(f"{m['base']}: not built (no files block)")
                continue
            ids = {e["id"] for e in m["elements"]}
            n_elems += len(ids)
            for key in ("viewport", "annotated"):
                if not (d / files[key]).exists():
                    fails.append(f"{d.name}/{files[key]} missing")
            if m["slices"] and not files["long"]:
                fails.append(f"{m['base']}: scrolls but has no stitched long image")
            for n in files["long"] + files["long_annotated"] + [x["file"] for x in m["slices"]]:
                if not (d / n).exists():
                    fails.append(f"{d.name}/{n} missing")
            # numbers: what is drawn is in the table, and every table row is drawn somewhere
            drawn = set(files["on_viewport"]) | set(files["on_long"])
            if not drawn <= ids:
                fails.append(
                    f"{m['base']}: numbers on the image but not in the table: {sorted(drawn - ids)}"
                )
            if ids - drawn:
                fails.append(f"{m['base']}: table rows never drawn: {sorted(ids - drawn)}")
            rows = (
                set(
                    re.findall(
                        r"^\| (E\d+) \|",
                        spec.split(
                            f'### State "{m["state"]}" · {m["role"]} · {m["lang"]} · {m["viewport"]}'
                        )[1]
                        .split("###")[0]
                        .split("## 5.")[0],
                        re.M,
                    )
                )
                if f'### State "{m["state"]}" · {m["role"]} · {m["lang"]} · {m["viewport"]}' in spec
                else set()
            )
            if rows != ids:
                fails.append(
                    f"{m['base']}: spec table rows differ from the elements ({len(rows)} vs {len(ids)})"
                )
            for c in m["checks"]:
                if not c.get("known"):
                    fails.append(f"{m['base']}: {c['rule']} {c.get('detail', '')}")
        for img in d.glob("*.png"):
            n_images += 1
            if img.stat().st_size > MAX_BYTES:
                fails.append(f"{d.name}/{img.name} is over 4 MB")
            with Image.open(img) as im:
                if ImageStat.Stat(im.convert("L")).stddev[0] < 2.0:
                    fails.append(f"{d.name}/{img.name} looks blank")

    # no secret or personal data in any text file of the pack
    for p in list(PACK.rglob("*.md")) + list(PACK.rglob("*.json")) + [PACK / "manifest.yaml"]:
        if p.name == "capture-index.json":
            continue
        for m in SECRET.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            if not any(x in m.group(0) for x in SAFE_EMAILS):
                fails.append(
                    f"{p.relative_to(PACK)}: looks like a secret or personal data: {m.group(0)[:20]}"
                )
                break

    print(
        f"stitch pack: {len(screens)} screens, {n_states} states, {n_images} images, {n_elems} elements described, {len(fails)} failures"
    )
    for f in fails[:60]:
        print("  FAIL", f)
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
