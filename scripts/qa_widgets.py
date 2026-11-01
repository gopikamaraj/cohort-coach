"""Build docs/build/qa/WIDGETS.md: every widget on the demo path, from the code.

For each screen on the demo path (the list below, with its roles and states written by hand), the
script lists every element that carries a `data-testid`: its kind (button, link, input, select,
tab, chip, card, table, drawer, dialog, player, list, ...), the string key of its label when the
label is on the same element, and that label in English. The QA tests (e2e/demo-path*.spec.ts)
use the same test ids, so this file is the checklist they walk.

    python scripts/qa_widgets.py          # rewrite docs/build/qa/WIDGETS.md
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "apps" / "pwa" / "src"
OUT = ROOT / "docs" / "build" / "qa" / "WIDGETS.md"
EN: dict[str, str] = json.loads((ROOT / "strings" / "en.json").read_text(encoding="utf-8"))

ALL_TEACHER = "Teacher, Mentor, Judge (as teacher)"


@dataclass(frozen=True)
class Screen:
    sid: str  # INVENTORY.md id
    name: str
    route: str
    files: tuple[str, ...]
    roles: str
    states: str  # the states the screen must handle, in words
    ai: str  # what needs the AI here, and what happens when it is off


SCREENS: tuple[Screen, ...] = (
    Screen("X1", "Landing page and role picker", "#/roles", ("screens/Landing.tsx",),
           "Everyone (first screen)", "default; scope dialog open; offline (cached shell)",
           "No AI."),
    Screen("-", "App shell: header, navigation, demo bar", "every route",
           ("App.tsx", "components/parts.tsx", "components/DemoPanel.tsx"),
           "Every role; tabs differ by role (teacher: Home, Papers, Enter check, My class, "
           "Practice, My programme, History; officer has no Papers)",
           "online, offline, waiting to send; demo bar on demo steps only; More sheet on a phone",
           "Header badge says AI: recorded answers or AI: off when the AI is not live."),
    Screen("J1", "Judge mode", "#/judge", ("screens/Judge.tsx",), "Judge",
           "default; simulated class loaded; offline", "No AI."),
    Screen("X36", "Demo flow (Demo Studio)", "#/demo?step=n", ("screens/DemoStudio.tsx",),
           "Judge (runs as teacher, coach, officer by step)",
           "each step: empty, loading (named loader), done, error with what to do; reset",
           "Sheet 1 read, lesson 1 draft, chat draft and lesson 2 draft use the AI; each shows "
           "Recorded AI answer when replayed and a fallback line when off."),
    Screen("X37", "Demo entry and review drawer", "#/demo?step=4 and 5",
           ("components/DemoEntry.tsx",), "Judge (as teacher)",
           "roll list per status (not entered, read needs review, approved, absent); drawer "
           "open; busy; error; off",
           "Read sheet 1 and Re-read use the AI; off: disabled with a reason, Auto-fill and "
           "typing still work."),
    Screen("T1", "Home", "#/home", ("screens/Home.tsx",), ALL_TEACHER,
           "no class; class loaded; check not entered; offline", "No AI."),
    Screen("X34", "Papers", "#/papers", ("screens/Papers.tsx",),
           "Teacher, Mentor, Coach (no officer)",
           "empty list; list with filters; create (two routes); review queue (coach); error",
           "Import from a PDF uses the AI (call 16); Generate from rules needs none."),
    Screen("X35", "Generate a paper", "#/papers (Create a paper, Generate from rules)",
           ("components/PaperMaker.tsx",), "Teacher, Mentor, Coach",
           "intake form; making (loader); made: preview, key, coverage, twin; error",
           "No AI: code makes the paper and its key."),
    Screen("X38", "Import a paper from a PDF", "#/papers (Create a paper, Import)",
           ("components/PaperImport.tsx",), "Teacher, Mentor, Coach",
           "upload; reading (loader); review table; blocking question open; confirmed; error; "
           "off", "Reads the printed questions with call 16; off: upload disabled with a reason."),
    Screen("X39", "Paper details, Assign, Assigned to you, Choose a paper", "#/papers, #/check",
           ("components/PaperHubParts.tsx",), "Teacher, Mentor, Coach",
           "tabs; assign within scope; nothing assigned (empty); error", "No AI."),
    Screen("T2", "Start a check and Enter check", "#/check",
           ("components/StartCheck.tsx", "screens/Check.tsx", "components/AddSheets.tsx",
            "components/SheetDrawer.tsx"), ALL_TEACHER,
           "choose a paper; entering (one roll list with data and approval states); absent; "
           "camera or a folder of pictures; the sheet drawer; Finish gated; finished; reopened; "
           "offline",
           "Reading a picture uses call 8; off: camera and folder disabled with a reason, "
           "typing still works."),
    Screen("T3", "What my class gets wrong", "#/cards", ("screens/Cards.tsx",
           "components/stages.tsx"), ALL_TEACHER, "no check yet (empty); results; simulated label",
           "No AI: counts come from code."),
    Screen("X14", "My programme", "#/programme", ("screens/Programme.tsx",), ALL_TEACHER,
           "not placed yet; placed; offline", "No AI."),
    Screen("T5", "Practice Class", "#/practice",
           ("screens/Practice.tsx", "components/practice.tsx", "components/breakit.tsx"),
           ALL_TEACHER + "; judge panel for judges only",
           "intro; starting; playing; paused; offline; error; feedback",
           "Child lines (call 1), move labels (call 2), checker (call 7), feedback (call 3); off: "
           "set lines, moves not recognised, a note says so."),
    Screen("-", "Two classes to a cohort", "#/two-classes", ("screens/TwoClasses.tsx",),
           "Judge (view as T1, T2, T3, C1, M1, M2, officer)",
           "five steps; each person's view; offline queue; error",
           "Lesson drafting (call 5) and chat drafts; off: the code template and a person."),
    Screen("X13", "Cohort chat", "#/cohort", ("screens/Cohort.tsx",),
           "Teacher, Mentor, Coach (moderation)", "empty thread; posts; held post; offline queue",
           "No AI writes thread posts."),
    Screen("X21", "Coach and mentor home", "#/coach, #/mentor", ("screens/RoleScreens.tsx",),
           "Coach, Mentor", "no cohorts; cohorts", "No AI."),
    Screen("P3", "Review queue", "#/review", ("screens/Review.tsx",), "Coach, Officer",
           "empty; items; approve; return with a reason", "Shows AI drafts; approval is human."),
    Screen("P1", "SCERT officer dashboard", "#/officer",
           ("screens/OfficerHome.tsx", "components/OfficerCohorts.tsx"), "Officer",
           "simulated block; cells under 5 hidden; no names", "No AI."),
    Screen("-", "Before and after (post-test)", "#/demo?step=12", ("components/BeforeAfter.tsx",),
           "Judge (as teacher)", "no post-test; results with the small-sample note", "No AI."),
    Screen("X29", "Assistant", "drawer from the header; #/assistant for judges",
           ("screens/Assistant.tsx",), "Every role, scoped by the server",
           "suggested questions; answer with sources; abstains with no source; offline",
           "Answers from repository documents; never confirms, approves or deletes."),
    Screen("X31-X32", "First-run name sheet and Feedback", "every route (tester links)",
           ("components/TesterUI.tsx",), "Every role on a public demo or tester link",
           "first run; skipped; feedback sheet; offline queue", "No AI."),
    Screen("X33", "Testing evidence", "#/testing", ("screens/TestingEvidence.tsx",), "Judge",
           "no data; counts and charts with text versions", "No AI."),
)

_TESTID = re.compile(r'data-testid=(?:"([^"]+)"|\{`([^`]+)`\}|\{"([^"]+)"\})')
_TR = re.compile(r'tr\("([a-z0-9_.]+)"')
_TAG = re.compile(r"<([A-Za-z][A-Za-z0-9.]*)\b")

KINDS = {
    "button": "button", "a": "link", "input": "input", "select": "select", "textarea": "text box",
    "audio": "audio player", "img": "image", "table": "table", "ul": "list", "ol": "list",
    "li": "list item", "article": "card", "section": "section", "aside": "panel",
    "details": "disclosure", "fieldset": "group", "label": "label", "p": "text", "span": "chip",
    "strong": "text", "h1": "heading", "h2": "heading", "h3": "heading", "div": "block",
    "nav": "navigation", "dialog": "dialog", "form": "form", "time": "time",
}


def _kind(tag: str, chunk: str, testid: str) -> str:
    if 'role="tab"' in chunk:
        return "tab"
    if 'role="dialog"' in chunk or "drawer" in testid:
        return "drawer" if "drawer" in testid else "dialog"
    if tag == "input":
        m = re.search(r'type="([a-z]+)"', chunk)
        t = m.group(1) if m else "text"
        return {"checkbox": "toggle", "radio": "choice", "file": "file picker"}.get(t, "input")
    if tag == "span" and "chip" not in chunk:
        return "text"
    if tag[0].isupper():
        return f"component <{tag}>"
    return KINDS.get(tag, tag)


def widgets(path: Path) -> list[tuple[str, str, str, str]]:
    text = path.read_text(encoding="utf-8")
    rows: list[tuple[str, str, str, str]] = []
    for m in _TESTID.finditer(text):
        testid = next(g for g in m.groups() if g)
        testid = re.sub(r"\$\{[^}]+\}", "{n}", testid)
        start = text.rfind("<", 0, m.start())
        tag_m = _TAG.match(text, start)
        tag = tag_m.group(1) if tag_m else "?"
        # the element's own text: from its opening tag to the next opening or closing tag after it
        end = text.find(">", m.end())
        after = text[end + 1 : end + 400]
        body = after.split("</", 1)[0]
        chunk = text[start : m.end() + 200]
        keys = _TR.findall(chunk.split(">", 1)[0] + ">" + body)
        key = keys[0] if keys else ""
        label = EN.get(key, "")
        rows.append((testid, _kind(tag, chunk, testid), key, label))
    seen: set[str] = set()
    unique = []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)
    return unique


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def build() -> str:
    lines = [
        "# Widget inventory: the demo path",
        "",
        "Generated by `python scripts/qa_widgets.py` from the code (every element with a "
        "`data-testid` on each screen of the demo path) and from "
        "`docs/design/stitch/INVENTORY.md` (screen ids). The roles, states and AI line of each "
        "screen are written in the script. A label column is empty when the visible text comes "
        "from data (a number, a name of a paper) or from a child component. This is the "
        "checklist for `e2e/demo-path.spec.ts` (recorded AI answers), "
        "`e2e/demo-path-ai-off.spec.ts` (AI off) and `docs/build/reports/QA-DEMO.md`.",
        "",
        "Every widget must also meet the shared rules: a visible or accessible label; 44 px "
        "touch target (48 px primary buttons); disabled only with a reason on screen; an error "
        "message that says what happened and what to do; no raw code or stack trace; English, "
        "Hindi and Tamil text from `strings/`.",
        "",
    ]
    total = 0
    for s in SCREENS:
        lines += [
            f"## {s.sid} · {s.name}",
            "",
            f"- **Route:** {s.route}",
            f"- **Files:** {', '.join(f'`apps/pwa/src/{f}`' for f in s.files)}",
            f"- **Roles that see it:** {s.roles}",
            f"- **States:** {s.states}",
            f"- **AI:** {s.ai}",
            "",
            "| Test id | Kind | Label key | Label (English) |",
            "| --- | --- | --- | --- |",
        ]
        for f in s.files:
            for testid, kind, key, label in widgets(SRC / f):
                lines.append(
                    f"| `{cell(testid)}` | {cell(kind)} | {f'`{key}`' if key else ''} | "
                    f"{cell(label)} |"
                )
                total += 1
        lines.append("")
    lines.insert(2, f"{len(SCREENS)} screens, {total} widgets with a test id.\n")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
