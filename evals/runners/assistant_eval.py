"""The assistant eval: scope, retrieval, refusal and citation correctness, per role. No model is called.

    python -m evals.runners.assistant_eval            write evals/assistant_eval.md
    python -m evals.runners.assistant_eval --check    exit 1 if that file is out of date

Per role: 10 on-scope questions (the judge: 30 rubric-aligned ones), 3 leak probes and 3 out-of-scope
questions (evals/sets/assistant.yaml). For every answer it records whether the cited source is the
right one, whether the status labels are right, whether leak probes and out-of-scope questions were
refused, and for the judge whether the cited slide and video time are correct.

This runs the retrieval and policy path that answers every typed question when no live model is
available. The wording of a live model answer (call 14) is not scored here: that waits for a live run
and is shown as pending. The numbers are written by this program from the run; none is typed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["AI_MODE"] = "recorded"  # never a paid call from an eval that has no model in it
os.environ["ASSISTANT_SESSION_MAX_PER_HOUR"] = "0"

from services.assistant import answer, retrieve  # noqa: E402
from services.assistant.scopes import ROLES, scopes  # noqa: E402

SET = ROOT / "evals" / "sets" / "assistant.yaml"
OUT = ROOT / "evals" / "assistant_eval.md"


def scope_paths(role: str) -> set[str]:
    return {c.path for c in retrieve.chunks_in(scopes()[role])}


def right_source(a: answer.Answer, role: str, expect: str | list[str]) -> bool:
    """A cited page of the role's own whose heading holds the expected words (any one of several
    acceptable ones, where two pages both answer the question)."""
    paths = scope_paths(role)
    wanted = [expect] if isinstance(expect, str) else expect
    return any(
        s["type"] == "file" and s["path"] in paths and w.lower() in (s.get("heading") or "").lower()
        for s in a.sources
        for w in wanted
    )


def nothing_outside(a: answer.Answer, role: str) -> bool:
    """The hard guarantee: every source is a file inside the scope; and, outside the judge scope, no
    slide, no video time and no status label (those belong to the judge's corpus)."""
    paths = scope_paths(role)
    for s in a.sources:
        if s["type"] == "file" and s.get("heading") is not None and s["path"] not in paths:
            return False
        if role != "judge" and s["type"] in ("slide", "video"):
            return False
    if role != "judge" and a.status_labels:
        return False
    return "sk-ant" not in a.answer


def topic_words(text: str) -> set[str]:
    return set(retrieve.tokens(text))


def judge_checks(a: answer.Answer, rows: list[str], lib: answer.Library) -> dict[str, bool]:
    labelled = {s["row"] for s in a.status_labels}
    hit = [r for r in rows if r in labelled]
    slides = {s["slide_no"] for s in a.sources if s["type"] == "slide"}
    times = {s["ts_start"] for s in a.sources if s["type"] == "video"}
    known_slides = {int(k) for k in lib.submission["slides"]}
    known_times = {
        int(t[:2]) * 60 + int(t[3:])
        for t in lib.submission["segments"]
        if int(t[:2]) * 60 + int(t[3:]) < lib.submission["video"]["length_s"]
    }
    want_slides = {n for r in hit for n in lib.rows[r]["slides"]}
    want_times = {int(t[:2]) * 60 + int(t[3:]) for r in hit for t in lib.rows[r]["video"]}
    slide_text = {
        c.slide_no: c.heading + " " + c.text
        for c in retrieve.chunks_in(scopes()["judge"])
        if c.kind == "slide" and c.slide_no is not None
    }
    claim_words = (
        set().union(
            *(topic_words(lib.rows[r]["claim"] + " " + lib.rows[r]["feature"]) for r in labelled)
        )
        if labelled
        else set()
    )
    return {
        "row": bool(hit),
        "labels": all(s["status"] == lib.rows[s["row"]]["status"] for s in a.status_labels),
        "slide": slides <= known_slides and want_slides <= slides,
        "slide_topic": all(
            topic_words(slide_text[n]) & claim_words for n in slides if n in slide_text
        ),
        "video": times <= known_times and want_times <= times,
    }


def run() -> dict[str, Any]:
    data = yaml.safe_load(SET.read_text(encoding="utf-8"))
    lib = answer.library()
    out: dict[str, Any] = {}
    for role in ROLES:
        spec, scope = data[role], scopes()[role]
        res: dict[str, Any] = {"on_scope": [], "rubric": [], "leaks": [], "out_of_scope": []}
        for item in spec.get("on_scope", []):
            a = answer.ask(scope, text=item["q"])
            res["on_scope"].append(
                {
                    "q": item["q"],
                    "ok": right_source(a, role, item["expect"]),
                    "abstained": a.abstained,
                }
            )
        for item in spec.get("rubric", []):
            a = answer.ask(scope, text=item["q"])
            res["rubric"].append(
                {
                    "q": item["q"],
                    "rows": item["rows"],
                    "abstained": a.abstained,
                    **judge_checks(a, item["rows"], lib),
                }
            )
        for item in spec["leaks"]:
            a = answer.ask(scope, text=item["q"])
            res["leaks"].append(
                {"q": item["q"], "clean": nothing_outside(a, role), "refused": a.abstained}
            )
        for item in spec["out_of_scope"]:
            a = answer.ask(scope, text=item["q"])
            res["out_of_scope"].append({"q": item["q"], "refused": a.abstained})
        out[role] = res
    return out


def count(items: list[dict[str, Any]], key: str) -> str:
    return f"{sum(1 for i in items if i[key])} of {len(items)}"


def render(res: dict[str, Any]) -> str:
    lines = [
        "# Assistant eval",
        "",
        "Generated by `python -m evals.runners.assistant_eval` from `evals/sets/assistant.yaml`; do not edit by hand.",
        "",
        "What this measures: the path that answers every typed question when no live model is available (retrieval inside the",
        "role's scope, the refusal rule, and the citations and status labels that code builds). No model is called.",
        "What it does not measure: the wording of a live model's answer (call 14). That needs a live run and is **pending**.",
        "Every number below is counted from this run.",
        "",
        "## Per role",
        "",
        "| Role | On-scope: right source cited | Leak probes: nothing from outside the scope shown | Leak probes: refused | Out of scope: refused |",
        "| --- | --- | --- | --- | --- |",
    ]
    for role in ROLES:
        r = res[role]
        on = (
            count(r["rubric"], "row") + " (rubric rows labelled)"
            if role == "judge"
            else count(r["on_scope"], "ok")
        )
        lines.append(
            f"| {role} | {on} | {count(r['leaks'], 'clean')} | {count(r['leaks'], 'refused')} | {count(r['out_of_scope'], 'refused')} |"
        )
    j = res["judge"]["rubric"]
    lines += [
        "",
        "## Judge guide: 30 rubric-aligned questions",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| The expected rubric row is labelled | {count(j, 'row')} |",
        f"| Every status label equals its row's status (never stronger) | {count(j, 'labels')} |",
        f"| Cited slide numbers exist and include the row's slides | {count(j, 'slide')} |",
        f"| Each cited slide is about the claim (shares its topic words) | {count(j, 'slide_topic')} |",
        f"| Cited video times exist, are inside the video, and include the row's times | {count(j, 'video')} |",
        "",
        "Slide numbers and video times are provisional until the final deck and video exist (`docs/RUBRIC_MAP.md`).",
        "",
        "## Misses",
        "",
        "Each line is a question that missed a check, so a reader can see what to improve. Leaks are only a miss in the",
        "'nothing from outside the scope shown' column; a leak probe that is answered from the role's own pages is not a leak.",
        "",
    ]
    misses: list[str] = []
    for role in ROLES:
        r = res[role]
        misses += [
            f"- {role}, on-scope, wrong or no source: {i['q']}"
            for i in r["on_scope"]
            if not i["ok"]
        ]
        for i in r["rubric"]:
            bad = [k for k in ("row", "labels", "slide", "slide_topic", "video") if not i[k]]
            if bad:
                misses.append(f"- judge, rubric ({', '.join(bad)}): {i['q']}")
        misses += [f"- {role}, LEAK: {i['q']}" for i in r["leaks"] if not i["clean"]]
        misses += [
            f"- {role}, leak probe answered from its own pages instead of refusing: {i['q']}"
            for i in r["leaks"]
            if i["clean"] and not i["refused"]
        ]
        misses += [
            f"- {role}, out of scope but answered: {i['q']}"
            for i in r["out_of_scope"]
            if not i["refused"]
        ]
    lines += misses or ["None."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    text = render(run())
    if "--check" in argv:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("assistant_eval.md is current" if ok else "assistant_eval.md is OUT OF DATE")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
