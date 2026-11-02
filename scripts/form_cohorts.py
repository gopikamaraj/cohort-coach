# ruff: noqa: E501
"""Form the cohorts now: the same thing the officer's "Create cohorts" button does, against DATABASE_URL.

    .\\run-backend-cloud-db.ps1 -Script form_cohorts.py

For every mistake that two or more entered classes show (latest term) it makes one cohort, once. It prints
names and class counts only."""

from __future__ import annotations

import os
import sys

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api.cohorts.class_only import form_cohorts  # noqa: E402
from services.api.db import make_engine  # noqa: E402


def main() -> int:
    with Session(make_engine()) as db:
        out = form_cohorts("officer", db)
    for c in out["created"]:
        print(f"Created: {c['name']} ({c['classes']} classes, {c['children_checked']} children checked)")
    print(f"Already formed: {out['already']}")
    if out["waiting"]:
        print(f"Shown by one class only (waiting): {', '.join(out['waiting'])}")
    if not out["created"] and not out["already"]:
        print("No mistake is shown by two or more classes yet, so nothing was formed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
