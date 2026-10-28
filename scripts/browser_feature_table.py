"""Groups the browser feature tests into features and writes docs/evidence/browser_features.md.

Reads docs/evidence/browser_qa/e2e.json, written by a real run:
  cd apps/pwa && SCREENSHOTS=1 PLAYWRIGHT_JSON_OUTPUT_NAME=../../docs/evidence/browser_qa/e2e.json \
      npx playwright test --reporter=list,json
and the crawl report (docs/evidence/browser_qa/report.json). No status is typed by hand: a feature
passes only if every test mapped to it passed, and a test that maps to no feature is listed so the
map can never hide one.
"""

# ruff: noqa: E501  (the Markdown lines this script writes are long sentences)
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "docs" / "evidence" / "browser_qa"
OUT = ROOT / "docs" / "evidence" / "browser_features.md"

# (area, feature, pages, [(spec, title pattern)]). Patterns are regular expressions on the test title.
FEATURES: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "Entry",
        "Landing page: role cards, scope dialog, deep links, layout",
        "#/roles",
        [("landing", ".")],
    ),
    (
        "Entry",
        "Role and language chosen on the landing page only",
        "#/roles, all",
        [("app", "landing page only"), ("app", "each role has its own home")],
    ),
    (
        "Entry",
        "Language switch (en / hi / ta) and page language",
        "all",
        [("app", "languages switch at runtime")],
    ),
    (
        "Entry",
        "Guided tour: steps, skip and back, resume, role walk-throughs",
        "#/tour",
        [("tour", ".")],
    ),
    (
        "Judge",
        "Judge mode: simulated class, Advance to Term 2, Simulate offline",
        "#/judge, #/home, #/cards",
        [("app", "judge mode loads"), ("app", "Advance to Term 2"), ("app", "Simulate offline")],
    ),
    (
        "Judge",
        "AI map and audit trail (metadata only)",
        "#/aimap, #/audit",
        [("practice", "AI map shows")],
    ),
    (
        "Judge",
        "Try to break it (pre-filter explanations)",
        "#/aimap, #/practice",
        [("hints", "try to break it")],
    ),
    (
        "Teacher",
        "Check entry: keypad, any-script digits, blank / can't read, autosave",
        "#/check",
        [
            ("check", "number keyboard|blank and can't read|list of sheets"),
            ("app", "10-child check|autosaved"),
        ],
    ),
    (
        "Teacher",
        "Check entry: absent children and missed-the-teaching tags",
        "#/check",
        [("check", "absent|missed the teaching")],
    ),
    (
        "Teacher",
        "Answer-sheet photo: fill, unsure boxes, failure and offline fallbacks",
        "#/check",
        [("photo", ".")],
    ),
    (
        "Teacher",
        "Stage of breakdown on the error card; sheets never leave the phone",
        "#/check, #/cards",
        [("stages", ".")],
    ),
    (
        "Teacher",
        "Error cards with counts (never a percentage); card flag and speaker toast",
        "#/cards",
        [("app", "judge mode loads"), ("profile", "speaker icon")],
    ),
    (
        "Teacher",
        "My programme and What I entered (history)",
        "#/programme, #/history",
        [
            (
                "programme",
                "My programme|no check yet|What I entered|filled from a photo|after trying it",
            )
        ],
    ),
    (
        "Teacher",
        "Lesson audio saved on the phone, plays offline",
        "lesson card",
        [("lesson-audio", ".")],
    ),
    (
        "Practice Class",
        "Text rehearsal end to end with feedback quoting her words",
        "#/practice",
        [
            (
                "practice",
                "rehearsal of 7 turns|retry uses|class's own counts|says what she is practising",
            )
        ],
    ),
    (
        "Practice Class",
        "Frozen children strip and section tabs (Class, Materials, Goal, Judge)",
        "#/practice",
        [
            ("practice", "rehearsal of 7 turns|says what she is practising|AI-layers overlay"),
            ("review", "no English words"),
            ("hints", "try with hints"),
        ],
    ),
    (
        "Practice Class",
        "Voice: hold to speak, short-tap guard, fallback to typing, 2G start",
        "#/practice",
        [("voice", ".")],
    ),
    (
        "Practice Class",
        "Cue card, hints, AI-layers overlay (judges only)",
        "#/practice",
        [("review", "cue card"), ("hints", "try with hints"), ("practice", "AI-layers overlay")],
    ),
    (
        "Practice Class",
        "Privacy: no transcript in server logs; consent before AI; thumbs stay on phone",
        "#/practice",
        [
            ("practice", "request log holds no transcript|feedback thumbs"),
            ("profile", "asks before using AI"),
        ],
    ),
    (
        "Practice Class",
        "Paused and offline states (recorded sample, nothing sent)",
        "#/practice",
        [("practice", "paused|offline, practice")],
    ),
    (
        "Practice Class",
        "Rehearsal review: recorded on phone, tagged, replayed, deleted, again",
        "#/practice (Review)",
        [("review", "recorded on the phone|again from the review")],
    ),
    (
        "Practice Class",
        "Language of the practice screen and of the next rehearsal",
        "#/practice",
        [("review", "language switch changes|no English words")],
    ),
    (
        "Practice Class",
        "Model run / Watch: AI label, move tags, two styles, autoplay",
        "#/watch",
        [("watch", ".")],
    ),
    (
        "Profile and privacy",
        "Consent: nothing on by default, versioned, counts wait for consent",
        "#/profile, #/privacy",
        [("profile", "nothing is on by default|not sent until she agrees")],
    ),
    (
        "Profile and privacy",
        "Several classes; persistent storage; data used and cost",
        "#/profile",
        [("profile", "several classes|keep her data|data used")],
    ),
    (
        "Profile and privacy",
        "Backup export / restore (passphrase) and erase everything",
        "#/profile",
        [("profile", "export then restore|erase everything")],
    ),
    (
        "Profile and privacy",
        "Feedback form reaches the admin; refuses personal details",
        "#/profile, #/admin",
        [("profile", "feedback needs her switch")],
    ),
    (
        "Other roles",
        "Coach and mentor screens: counts only, no percentage",
        "#/coach, #/mentor",
        [("profile", "role screens")],
    ),
    (
        "Other roles",
        "Review queue: age, return reason, edit checks, two-key switch-on, hi / ta",
        "#/review",
        [("review-queue", ".")],
    ),
    (
        "Other roles",
        "Cohort chat: join consent, name filter, report, coach moderation, read-only",
        "#/cohort",
        [("cohort", ".")],
    ),
    (
        "Other roles",
        "Officer: funnel with sources, verdicts, error map under 5 hidden, cohort lifecycle",
        "#/officer",
        [("officer", ".")],
    ),
    (
        "Pilot mode",
        "Sign-in, two pages only, consent gate, upload queue offline",
        "pilot",
        [("pilot", "pilot mode: sign-in|wrong key|consent is confirmed|no signal")],
    ),
    (
        "Pilot mode",
        "Intervention audio: approval gates sharing; lesson link; hi / ta; 44 px",
        "pilot",
        [
            (
                "pilot",
                "audio page|cannot share|share sheet|Hindi and Tamil|horizontal scroll|lesson link",
            )
        ],
    ),
    (
        "Real scenarios",
        "Installable PWA and works offline after first load",
        "all",
        [("app", "installable|works offline")],
    ),
    (
        "Real scenarios",
        "Layout: no sideways scroll 320-1280 px, bottom bar and More, phone column",
        "all",
        [("layout", "."), ("programme", "no sideways scrolling|wide screen")],
    ),
    (
        "Evidence",
        "Screenshot walk-throughs (en / hi / ta, desktop frame, Practice Class)",
        "many",
        [("screenshots", ".")],
    ),
]


def tests(report: dict[str, Any]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []

    def walk(suite: dict[str, Any], spec: str) -> None:
        spec = (
            Path(suite.get("file", spec)).stem.removesuffix(".spec") if suite.get("file") else spec
        )
        for s in suite.get("specs", []):
            for t in s.get("tests", []):
                results = t.get("results", [])
                status = results[-1]["status"] if results else "skipped"
                found.append({"spec": spec, "title": s["title"], "status": status})
        for child in suite.get("suites", []):
            walk(child, spec)

    for suite in report["suites"]:
        walk(suite, "")
    return found


def main() -> None:
    run = tests(json.loads((DIR / "e2e.json").read_text(encoding="utf-8")))
    crawl = json.loads((DIR / "report.json").read_text(encoding="utf-8"))
    totals = Counter(t["status"] for t in run)
    used: set[int] = set()
    rows = []
    for area, name, pages, rules in FEATURES:
        hit = [
            i
            for i, t in enumerate(run)
            if any(t["spec"] == spec and re.search(pat, t["title"]) for spec, pat in rules)
        ]
        used.update(hit)
        st = Counter(run[i]["status"] for i in hit)
        n = len(hit)
        if n == 0:
            status = "No test"
        elif st["passed"] == n:
            status = "Pass"
        elif st["failed"] or st["timedOut"]:
            status = "Fail"
        else:
            status = "Not run"
        rows.append(f"| {area} | {name} | {pages} | {st['passed']} of {n} | {status} |")
    unmapped = [t for i, t in enumerate(run) if i not in used]

    issues = [r for r in crawl if r.get("issues")]
    routes = sorted({r["route"] for r in crawl})
    out = [
        "# Browser features: status",
        "",
        "Generated by `scripts/browser_feature_table.py` from a real Playwright run (`docs/evidence/browser_qa/e2e.json`) and the route crawl (`docs/evidence/browser_qa/report.json`); do not edit by hand. The API ran in recorded and stub mode, so no paid call was made; live AI and Sarvam voice are not covered here.",
        "",
        f"Feature tests: {totals['passed']} passed, {totals['failed'] + totals['timedOut']} failed, {totals['skipped']} skipped, of {len(run)}.",
        f"Route crawl: {len(crawl)} page views ({len(routes)} routes, 3 languages, phone and desktop), {len(issues)} with issues.",
        "",
        "A feature passes only if every test mapped to it passed. One test can cover more than one feature.",
        "",
        "| Area | Feature | Pages | Tests passed | Status |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "## Crawl: every route",
        "",
        "| Route | Views | With issues |",
        "| --- | --- | --- |",
        *[
            f"| #/{r} | {sum(1 for x in crawl if x['route'] == r)} | {sum(1 for x in issues if x['route'] == r)} |"
            for r in routes
        ],
    ]
    if issues:
        out += [
            "",
            "### Crawl issues",
            "",
            *[
                f"- #/{r['route']} ({r.get('view', '')}, {r.get('lang', '')}): {'; '.join(r['issues'])}"
                for r in issues
            ],
        ]
    out += ["", "## Tests not mapped to a feature", ""]
    out += [f"- {t['spec']}: {t['title']} ({t['status']})" for t in unmapped] or ["None."]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} features, {len(unmapped)} unmapped tests")


if __name__ == "__main__":
    main()
