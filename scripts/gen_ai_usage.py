"""Regenerate section 4 of AI_USAGE.md (the call registry) from ai/registry.py.

    python scripts/gen_ai_usage.py [--check]

Only the text between the REGISTRY markers is rewritten; the rest of the file is hand-written and
kept honest by tests/test_ai_usage_doc.py. The fallback column is the one fact the registry does
not hold as a field, so it is listed here once and a test fails if a call has none.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.registry import CALLS  # noqa: E402

DOC = ROOT / "AI_USAGE.md"
START, END = "<!-- REGISTRY:START -->", "<!-- REGISTRY:END -->"

FALLBACKS: dict[int, str] = {
    1: "a template line from the engine's own numbers",
    2: "label `other` (changes nothing)",
    3: "a template card; nothing is shown that failed a check",
    4: "no card: the mentor is asked to try again or a coach is asked to help",
    5: "no draft: the lesson waits for a human; a line without a valid citation is dropped",
    6: "no digest this week",
    7: "fail goes to a human; nothing is released",
    8: "the teacher types the answers",
    10: "the move's own template line",
    11: "no draft: nothing is shown; the author is told which rule failed",
    12: "class unclear: no draft is made and a person answers",
    13: "no draft: the mentor or coach answers without one",
    14: "an extract from the retrieved passages, or no answer and where to look",
}


def cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def render() -> str:
    rows = [
        "| Id | Purpose | Model | Input | Output schema | Gates | Fallback |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in CALLS:
        rows.append(
            "| {id} | {purpose} | `{model}` | {inp} | `{schema}` | {gates} | {fb} |".format(
                id=c.id,
                purpose=cell(c.purpose),
                model=c.model,
                inp=cell(c.input),
                schema=c.output_model.__name__,
                gates=cell("; ".join(c.gates)),
                fb=cell(FALLBACKS[c.id]),
            )
        )
    return "\n".join(rows)


def build(current: str) -> str:
    head, rest = current.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n{render()}\n{END}{tail}"


def main(argv: list[str]) -> int:
    current = DOC.read_text(encoding="utf-8")
    new = build(current)
    if "--check" in argv:
        print("ok    AI_USAGE.md" if new == current else "STALE AI_USAGE.md: run gen_ai_usage.py")
        return 0 if new == current else 1
    DOC.write_text(new, encoding="utf-8", newline="\n")
    print("AI_USAGE.md: registry section regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
