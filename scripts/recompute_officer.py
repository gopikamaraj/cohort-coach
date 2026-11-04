"""Recompute every number on the officer page from the database, and compare it with what the page is given.

    python scripts/recompute_officer.py                 # reads DATABASE_URL (default dev.sqlite), writes nothing
    python scripts/recompute_officer.py --report docs/build/reports/OFFICER-NUMBERS.md

It works from the raw material only: each entered check's answers, the paper's own wrong-answer table, absent marks.
The calculation here is deliberately plain and does not call the engine's classifier (a child "shows" an error with two
or more hits on its probing items, "made it once" with one or more), so it checks the server rather than repeating it.

Two comparisons:
  A. The counts the PHONE saved with each class result (what the officer page used to add up) against the recomputed ones.
  B. The numbers the officer endpoint returns now against the recomputed ones (this must be zero mismatches).
It never writes to the database and never prints a nickname, class code or child.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _norm(raw: str) -> int | None:
    from engine.normalize import normalize_answer

    got = normalize_answer(raw if str(raw).strip() else None)
    return got if isinstance(got, int) else None


def plain_counts(items: list[dict[str, Any]], rows: list[list[str]], absent: list[int], only: set[int] | None = None) -> tuple[int, dict[str, int], dict[str, int]]:
    """Children checked; children with an error on two or more items; on one or more. `items` is the paper key."""
    skip = {int(i) for i in absent}
    checked, conf, once = 0, defaultdict(int), defaultdict(int)
    for i, row in enumerate(rows):
        if i in skip or not isinstance(row, list) or not any(str(c).strip() for c in row):
            continue
        checked += 1
        hits: dict[str, int] = defaultdict(int)
        for q, item in enumerate(items):
            if only is not None and int(item["n"]) not in only:
                continue
            ans = _norm(str(row[q]) if q < len(row) else "")
            if ans is None:
                continue
            for code in item["wrong"].get(str(ans), []):
                hits[code] += 1
        for code, n in hits.items():
            if n >= 1:
                once[code] += 1
            if n >= 2:
                conf[code] += 1
    return checked, dict(conf), dict(once)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--report", help="write a markdown report here")
    args = ap.parse_args()

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from services.api.db import make_engine
    from services.api.devicestore import UserDoc
    from services.papers import keys as paper_keys
    from services.papers.models import PaperRow

    url = os.environ.get("DATABASE_URL") or f"sqlite:///{ROOT / 'dev.sqlite'}"
    engine = make_engine(url)
    with Session(engine) as db:
        docs: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        for r in db.scalars(select(UserDoc).where(UserDoc.collection.in_(("profiles", "checks", "classes")))):
            docs[r.owner].setdefault(r.collection, {})[r.doc_id] = r.data if isinstance(r.data, dict) else {}
        # the most recent check of each class (by date saved), recomputed from its answers
        latest: dict[str, dict[str, Any]] = {}
        unreadable = 0
        for owner, d in docs.items():
            for prof in d.get("profiles", {}).values():
                check = d.get("checks", {}).get(str(prof.get("id")))
                paper = db.get(PaperRow, str(prof.get("formKey"))) if str(prof.get("formKey", "")).startswith("P-") else None
                if check is None or paper is None or not isinstance(check.get("children"), list):
                    # answers or paper are not here: the endpoint keeps the numbers the result was saved with, so so does this
                    if int(prof.get("childrenChecked") or 0):
                        unreadable += 1
                        key = f"{owner}/{prof.get('classId')}"
                        at = int((check or {}).get("updatedAt") or prof.get("createdAt") or 0)
                        if key not in latest or at > latest[key]["at"]:
                            sc = {k: int(v) for k, v in (prof.get("counts") or {}).items()}
                            so = {k: int(v) for k, v in ((prof.get("anyCounts") or prof.get("counts")) or {}).items()}
                            latest[key] = {"at": at, "checked": int(prof["childrenChecked"]), "conf": sc, "once": so, "stored_conf": sc, "stored_once": so, "stored_checked": int(prof["childrenChecked"]), "kept": True}
                    continue
                items = paper_keys.key_of(paper.id, paper.body, paper.check_code)["forms"][paper.id]["items"]
                checked, conf, once = plain_counts(items, check["children"], list(check.get("absent") or []))
                at = int(check.get("updatedAt") or prof.get("createdAt") or 0)
                key = f"{owner}/{prof.get('classId')}"
                if checked and (key not in latest or at > latest[key]["at"]):
                    latest[key] = {"at": at, "checked": checked, "conf": conf, "once": once, "stored_conf": {k: int(v) for k, v in (prof.get("counts") or {}).items()}, "stored_once": {k: int(v) for k, v in ((prof.get("anyCounts") or prof.get("counts")) or {}).items()}, "stored_checked": int(prof.get("childrenChecked") or 0)}

    mism_a = 0
    for c in latest.values():
        if c.get("kept"):
            continue
        if c["stored_checked"] != c["checked"] or c["stored_conf"] != c["conf"] or c["stored_once"] != c["once"]:
            mism_a += 1
    total_checked = sum(c["checked"] for c in latest.values())

    # B: what the officer endpoint returns now
    from fastapi.testclient import TestClient

    os.environ.setdefault("JUDGE_MODE", "1")
    from services.api.main import create_app

    client = TestClient(create_app())
    lines: list[str] = []
    mism_b = 0
    for rule, field in ((2, "conf"), (1, "once")):
        resp = client.get(f"/api/store/coach-summary?min_hits={rule}", headers={"X-User": "recompute-officer", "X-Role": "officer"})
        if resp.status_code == 401:
            client.post("/api/users/register", json={"nickname": "recompute-officer"})
            resp = client.get(f"/api/store/coach-summary?min_hits={rule}", headers={"X-User": "recompute-officer", "X-Role": "officer"})
        got = resp.json()["totals"] if resp.status_code == 200 else {"classes": -1, "children_checked": -1, "children_showing": {}}
        want: dict[str, int] = defaultdict(int)
        for c in latest.values():
            for code, n in c[field].items():
                want[code] += n
        ok = got["classes"] == len(latest) and got["children_checked"] == total_checked and dict(got["children_showing"]) == dict(want)
        mism_b += 0 if ok else 1
        lines.append(f"| officer totals, rule {rule} ({'confirmed' if rule == 2 else 'possible'}) | {len(latest)} classes, {total_checked} children checked, {dict(sorted(want.items()))} | {got['classes']} classes, {got['children_checked']} children checked, {dict(sorted(got['children_showing'].items()))} | {'match' if ok else 'MISMATCH'} |")

    out = [
        f"Database: {url.split('///')[-1] if url.startswith('sqlite') else '(hosted)'}; classes: {len(latest)}, of which {sum(1 for c in latest.values() if c.get("kept"))} have no answers or paper here and are taken as saved (nothing to recompute from); the other {sum(1 for c in latest.values() if not c.get("kept"))} are recomputed from their answers.",
        "",
        f"A. Counts saved by the phone with each class result against the recomputed ones: {mism_a} of {sum(1 for c in latest.values() if not c.get('kept'))} recomputed classes differ.",
        f"B. Numbers the officer endpoint returns now against the recomputed ones: {mism_b} mismatches.",
        "",
        "| Number | Recomputed from the answers | Officer endpoint | Result |",
        "| --- | --- | --- | --- |",
        *lines,
    ]
    text = "\n".join(out)
    print(text)
    if args.report:
        Path(args.report).write_text("# Officer numbers: recomputed from the database\n\nGenerated by `scripts/recompute_officer.py` (read only).\n\n" + text + "\n", encoding="utf-8")
    return 0 if mism_b == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
