# ruff: noqa: E501
"""List the classes in the cloud device store, and remove a teacher's whole set of documents.

    python scripts/store_classes.py                    list: one line per store key (nickname, class names, how many documents)
    python scripts/store_classes.py --drop-class 9f3a:"My class"   remove one class (its checks and results) from the store key starting with 9f3a
    python scripts/store_classes.py --delete 9f3a      delete every document under the key that starts with 9f3a (asks first; --yes skips)

DATABASE_URL must point at the database (`.\\run-backend-cloud-db.ps1 -Script store_classes.py` does that for the cloud one).
Only class names, nicknames and counts of documents are printed: no answers."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api.db import ClassCohort, make_engine  # noqa: E402
from services.api.devicestore import UserDoc  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delete", metavar="KEY_PREFIX", action="append", default=[], help="delete the documents of the store key starting with this (repeatable)")
    ap.add_argument("--drop-class", metavar="KEY_PREFIX:NAME", action="append", default=[], help="remove one class by name, with its checks and results")
    ap.add_argument("--set-term", metavar="KEY_PREFIX:TERM", action="append", default=[], help="set the term setting of one store key (for example 0524d3:1)")
    ap.add_argument("--delete-cohort", metavar="COHORT_ID", action="append", default=[], help="delete one cohort row (class_cohorts) by its id, for example cc-6a42b306b287")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    engine = make_engine()
    with Session(engine) as db:
        rows = db.scalars(select(UserDoc)).all()
        keys: dict[str, dict[str, object]] = {}
        for r in rows:
            k = keys.setdefault(r.owner, {"docs": 0, "classes": [], "nick": "", "checks": 0})
            k["docs"] = int(k["docs"]) + 1  # type: ignore[call-overload]
            if r.collection == "classes" and isinstance(r.data, dict):
                k["classes"].append(str(r.data.get("name") or r.doc_id))  # type: ignore[attr-defined]
            if r.collection == "checks":
                k["checks"] = int(k["checks"]) + 1  # type: ignore[call-overload]
            if r.collection == "settings" and r.doc_id == "nickname" and isinstance(r.data, dict):
                k["nick"] = str(r.data.get("value") or "")
        for key, k in sorted(keys.items()):
            print(f"{key[:6]}  nickname={k['nick'] or '-':20} classes={k['classes']}  checks={k['checks']}  docs={k['docs']}")
        for cid in args.delete_cohort:
            row = db.get(ClassCohort, cid)
            if row is None:
                print(f"No cohort {cid}.")
                continue
            if not args.yes and input(f"Delete cohort {cid} ({row.scope}, {row.errors})? Type yes: ").strip() != "yes":
                print("Skipped.")
                continue
            db.delete(row)
            db.commit()
            print(f"Deleted cohort {cid}.")
        for spec in args.set_term:
            prefix, _, term = spec.partition(":")
            hit = [k for k in keys if k.startswith(prefix)]
            if len(hit) != 1 or not term.isdigit():
                print(f"'{spec}': needs one matching key and a number; nothing changed.")
                continue
            row = db.get(UserDoc, (hit[0], "settings", "term"))
            before = row.data.get("value") if row is not None and isinstance(row.data, dict) else None
            if row is None:
                db.add(UserDoc(device=hit[0], collection="settings", doc_id="term", data={"key": "term", "value": int(term)}))
            else:
                row.data = {"key": "term", "value": int(term)}
            db.commit()
            print(f"Term of {hit[0][:6]}: {before} -> {int(term)}")
        for spec in args.drop_class:
            prefix, _, name = spec.partition(":")
            hit = [k for k in keys if k.startswith(prefix)]
            if len(hit) != 1:
                print(f"'{prefix}' matches {len(hit)} keys: nothing dropped.")
                continue
            mine = db.scalars(select(UserDoc).where(UserDoc.owner == hit[0])).all()
            ids = {r.doc_id for r in mine if r.collection == "classes" and isinstance(r.data, dict) and r.data.get("name") == name}
            others = [r.doc_id for r in mine if r.collection == "classes" and r.doc_id not in ids]
            gone = [r for r in mine if (r.collection == "classes" and r.doc_id in ids) or (r.collection in ("checks", "profiles") and isinstance(r.data, dict) and r.data.get("classId") in ids)]
            if not ids:
                print(f"No class named '{name}' under {hit[0][:6]}.")
                continue
            if not args.yes and input(f"Drop class '{name}' ({len(gone)} documents) from {hit[0][:6]}? Type yes: ").strip() != "yes":
                print("Skipped.")
                continue
            for r in gone:
                db.delete(r)
            active = next((r for r in mine if r.collection == "settings" and r.doc_id == "activeClass"), None)
            if active is not None and isinstance(active.data, dict) and active.data.get("value") in ids:
                if others:
                    active.data = {"key": "activeClass", "value": others[0]}
                else:
                    db.delete(active)
            db.commit()
            print(f"Dropped '{name}' from {hit[0][:6]} ({len(gone)} documents).")
        for prefix in args.delete:
            hit = [k for k in keys if k.startswith(prefix)]
            if len(hit) != 1:
                print(f"'{prefix}' matches {len(hit)} keys: nothing deleted for it.")
                continue
            if not args.yes and input(f"Delete all {keys[hit[0]]['docs']} documents of {hit[0][:6]}? Type yes: ").strip() != "yes":
                print("Skipped.")
                continue
            db.execute(delete(UserDoc).where(UserDoc.owner == hit[0]))
            db.commit()
            print(f"Deleted {hit[0][:6]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
