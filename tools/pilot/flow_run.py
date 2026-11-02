"""The manual pilot run of the five flows, on the machine that holds the pilot folder.

    python -m tools.pilot.flow_run

Reads the hand-keyed answer file (data/pilot/pilot_answers.json, git-ignored), works out each
class's counts in memory with the engine (the same rule as the phone), and walks the five flows on
the real API in a throwaway database: T1 submits 3A, T2 submits 3B, the cohort forms, the coach
approves lesson 1, T1 answers Not yet and generates her next lesson, the coach approves it, T2 asks
in the chat with a made-up name, the coach answers, T1 sees it, and the coach's view is read.

No paid call: recorded AI answers and the stub voice. Nothing per child leaves this process: the
API receives class counts only. The result goes to data/pilot/evidence/flow-run.md (git-ignored),
and the console prints counts and pass or fail lines only, which are all the report may copy.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PILOT = Path(os.environ.get("PILOT_DEMO_DIR", str(ROOT / "data" / "pilot")))
RID = "run-00000000000a170b"  # a throwaway run in a temporary database
QUESTION_HI = "मीना 703 में से 468 घटाने पर 365 लिखती है। मैं क्या करूँ?"  # Meena is made up
REPLY_HI = "बच्चे से दस की गड्डियों से दिखाने को कहें।"


def class_rows(answer_file: dict[str, Any], code: str) -> list[list[Any]]:
    from engine.normalize import normalize_answer

    cls = next(c for c in answer_file["classes"] if c["class_code"] == code)
    rows = []
    for sheet in cls["sheets"]:
        if sheet["status"] != "entered" or not sheet["answers"]:
            continue
        by_q = {int(a["q"]): a.get("given") for a in sheet["answers"]}
        rows.append(
            [
                normalize_answer(None if by_q.get(n) in (None, "") else str(by_q[n]))
                for n in range(1, 16)
            ]
        )
    return rows


def main() -> int:
    path = PILOT / "pilot_answers.json"
    if not path.exists():
        print("No pilot answer file on this machine: nothing to run.")
        return 1
    os.environ.update({"JUDGE_MODE": "1", "AI_MODE": "recorded", "SPEECH_MODE": "stub"})
    tmp = Path(tempfile.mkdtemp(prefix="flow-run-"))
    os.environ["DEMO_CACHE_DIR"] = str(tmp / "cache")

    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from ai.client import CallContext
    from services.api import practice as practice_api
    from services.api.db import Base, make_engine
    from services.api.main import create_app
    from services.api.profiles import get_session
    from services.cohort_run import service as svc

    engine = make_engine(f"sqlite:///{tmp / 'run.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(mode="recorded")
    c = TestClient(app)
    api = f"/api/cohort-run/runs/{RID}"
    answer_file = json.loads(path.read_text(encoding="utf-8"))
    lines: list[str] = []
    ok_all = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok_all
        ok_all = ok_all and cond
        lines.append(f"- {'PASS' if cond else 'FAIL'} {name}{': ' + detail if detail else ''}")

    with factory() as db:
        svc.new_run(db, RID, source="pilot")
    counts = {}
    for code, teacher in (("3A", "T1"), ("3B", "T2")):
        with factory() as db:
            row = db.get(svc.CohortRun, RID)
            cc = svc.counts_from_rows(row, code, class_rows(answer_file, code))
        counts[code] = cc
        body = {
            "as": teacher,
            "synthetic": False,
            "children_checked": cc.children_checked,
            "counts": cc.counts,
            "possible": cc.possible,
        }
        v = c.post(f"{api}/classes/{code}/check", json=body).json()
        lines.append(
            f"- {code}: {cc.children_checked} checked; 2-item counts {cc.counts}; "
            f"one-question counts {cc.possible}; status after submit: {v['status']}"
        )
    coach = c.get(api, params={"as": "C1"}).json()
    check(
        "Flow 1: a cohort forms after the second class",
        coach["status"] == "formed",
        coach["status"],
    )
    for k in coach.get("cohorts", []):
        lines.append(
            f"- cohort {k['error']}: {k['classes']} classes, {k['showing']} of "
            f"{k['checked']} children, labels {k['labels']}, mentor {k['mentor']}"
        )
    if coach["status"] != "formed":
        for cls in (c.get(api, params={"as": t}).json().get("class") or {} for t in ("T1", "T2")):
            lines.append(
                f"- {cls.get('code')}: track {cls.get('track')}; reasons "
                f"{ {e: r['code'] for e, r in (cls.get('errors') or {}).items()} }"
            )
    else:
        lessons = coach["lessons"]
        check(
            "Flow 2: lesson 1 per language, in review",
            all(x["status"] == "in_review" for x in lessons),
            ", ".join(f"{x['id']} {x['source']}" for x in lessons),
        )
        for x in lessons:
            c.post(f"{api}/lessons/{x['id']}/decide", json={"decision": "approve"})
        t1 = c.get(api, params={"as": "T1"}).json()
        first = t1["lessons"][0]
        check(
            "Flow 2: released to T1 with her class's numbers",
            first["status"] == "released" and bool(first["script"]) and "{{" not in first["script"],
        )
        c.post(f"{api}/lessons/{first['id']}/played", json={"as": "T1", "heard": True})
        c.post(
            f"{api}/lessons/{first['id']}/feedback",
            json={"as": "T1", "answer": "not_yet", "note": "Meena still writes 365"},
        )
        nxt = c.post(f"{api}/next", json={"as": "T1"}).json()
        check(
            "Flow 3: Not yet gives another approach",
            nxt["next"]["decision"]["mode"] == "other_approach",
            json.dumps(nxt["next"]["decision"]),
        )
        c.post(f"{api}/lessons/{nxt['next']['lesson']}/decide", json={"decision": "approve"})
        r = c.post(f"{api}/chat/ask", json={"as": "T2", "text": QUESTION_HI, "share": True}).json()
        check("Flow 4: the name is masked", "मीना" not in json.dumps(r, ensure_ascii=False))
        box = c.get(api, params={"as": "C1"}).json()["inbox"]["pending"]
        if box:
            c.post(f"{api}/chat/{box[0]['id']}/reply", json={"mode": "own", "text": REPLY_HI})
        shared = c.get(f"{api}/chat", params={"as": "T1"}).json()["cohort_shared"]
        check("Flow 4: T1 sees the shared answer", bool(shared and shared[0]["answers"]))
        final = c.get(api, params={"as": "C1"}).json()["cohorts"][0]
        check(
            "Flow 5: the coach sees counts",
            final["lesson1"]["feedback"]["not_yet"] == 1,
            json.dumps({k: final[k] for k in ("classes", "teachers", "showing", "checked")})
            + " feedback "
            + json.dumps(final["lesson1"]["feedback"])
            + " chat "
            + json.dumps(final["chat"]),
        )
    out = PILOT / "evidence" / "flow-run.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Pilot flow run (local, never commit)\n\nCounts and pass or fail lines only.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
