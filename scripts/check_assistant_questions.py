"""Pre-deploy gate for the assistant's reference: are its suggested questions right for each page
and role? Deterministic: no AI call, no network.

    python scripts/check_assistant_questions.py          report, exit 1 if anything is wrong
    python scripts/check_assistant_questions.py --json   the same, as JSON (for the refresh prompt)

Checks (the screens each role reaches are in docs/assistant_questions/screens.yaml):
  1. every route of the app (apps/pwa/src/lib/router.ts) is a screen in screens.yaml and a valid
     question screen, so no page falls back to generic questions;
  2. every question names screens that exist, and every role in screens.yaml has a question bank;
  3. each role has at least `min_questions` questions written for each screen it reaches (a
     question marked for any screen does not count: it is the fallback, not the page's own);
  4. the five questions the panel would show for a role on a screen are distinct;
  5. no suggested question's pre-written answer abstains (it must rest on a rubric row or a help
     page), so every question offered gets a real answer offline.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.assistant.questions import VALID_SCREENS, parse_bank, top_five  # noqa: E402
from services.assistant.scopes import scopes  # noqa: E402

ROUTER = ROOT / "apps" / "pwa" / "src" / "lib" / "router.ts"
MAP = ROOT / "docs" / "assistant_questions" / "screens.yaml"
INDEX = ROOT / "services" / "assistant" / "index"


def app_routes() -> list[str]:
    """The route names of the app: `/papers` is `papers`; `/roles` is the role picker, `landing`."""
    text = ROUTER.read_text(encoding="utf-8")
    block = re.search(r"export const ROUTES[^=]*=\s*\[(.*?)\]", text, re.S)
    assert block, "ROUTES not found in router.ts"
    names = re.findall(r'"/([a-z0-9-]+)"', block.group(1))
    return ["landing" if n == "roles" else n for n in names]


def check() -> dict[str, Any]:
    cfg = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    minimum = int(cfg["min_questions"])
    problems: list[str] = []
    gaps: list[dict[str, Any]] = []
    reached = {s for screens in cfg["roles"].values() for s in screens}
    for r in app_routes():
        if r in cfg.get("not_screens", []):
            continue
        if r not in VALID_SCREENS:
            problems.append(f"route '{r}' is not a valid question screen (questions.VALID_SCREENS)")
        if r not in reached:
            problems.append(f"route '{r}' is in no role's screen list (screens.yaml)")
    known = scopes()
    for role, screens in cfg["roles"].items():
        if role not in known:
            problems.append(f"role '{role}' has no assistant scope (assistant_scopes.yaml)")
            continue
        path = ROOT / known[role].question_bank
        bank = parse_bank(json.loads(path.read_text(encoding="utf-8")))
        for q in bank:
            for s in q.screens:
                if s not in VALID_SCREENS:
                    problems.append(f"{role}/{q.id}: unknown screen '{s}'")
        for screen in screens:
            if screen not in VALID_SCREENS:
                problems.append(f"{role}: screen '{screen}' is not a valid question screen")
                continue
            own = [q.id for q in bank if screen in q.screens]
            shown = top_five(bank, screen)
            if len({q.id for q in shown}) != len(shown):
                problems.append(f"{role}/{screen}: the top five repeat a question")
            if len(own) < minimum:
                gaps.append({"role": role, "screen": screen, "have": own, "need": minimum})
    curated = INDEX / "curated.json"
    if curated.exists():  # the pre-written answers (built by build_assistant_index.py)
        for role, answers in json.loads(curated.read_text(encoding="utf-8")).items():
            for qid, a in answers.items():
                if a.get("abstained"):
                    problems.append(f"{role}/{qid}: its pre-written answer abstains (no source)")
    return {"problems": problems, "gaps": gaps, "min_questions": minimum}


def main(argv: list[str]) -> int:
    out = check()
    if "--json" in argv:
        print(json.dumps(out, indent=1))
    else:
        for p in out["problems"]:
            print("PROBLEM", p)
        for g in out["gaps"]:
            have = f"{len(g['have'])} of {g['need']}"
            print(f"GAP     {g['role']:8} {g['screen']:12} {have} written for this screen")
        n = len(out["problems"]) + len(out["gaps"])
        print(f"{n} to fix" if n else "ok    every role has questions for each screen it reaches")
    return 1 if out["problems"] or out["gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
