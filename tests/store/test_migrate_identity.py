"""The identity migration may be run again: rows already parked under `unclaimed:` are left alone (a second prefix made
the value longer than the 32-character owner column on Postgres; SQLite never noticed)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

_spec = importlib.util.spec_from_file_location("migrate_identity", Path(__file__).resolve().parents[2] / "scripts" / "migrate_identity.py")
assert _spec and _spec.loader
mi = importlib.util.module_from_spec(_spec)
sys.modules["migrate_identity"] = mi
_spec.loader.exec_module(mi)


def test_a_row_already_parked_as_unclaimed_is_not_prefixed_again() -> None:
    engine = create_engine("sqlite://")
    parked = "unclaimed:6e783057bbd61c81"
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE kept_sheet (owner VARCHAR(32))"))
        conn.execute(text("INSERT INTO kept_sheet VALUES (:o), ('d-new')"), {"o": parked})
        plan = mi.Plan()
        mi.rekey(conn, plan, "kept_sheet", "owner", parked, mi.UNCLAIMED + parked)  # what a second run would try
        mi.rekey(conn, plan, "kept_sheet", "owner", "d-new", mi.UNCLAIMED + "d-new")  # a first run still parks it
        rows = sorted(r[0] for r in conn.execute(text("SELECT owner FROM kept_sheet")))
    assert rows == [parked, "unclaimed:d-new"]
    assert plan.counts["kept_sheet.owner"] == 1
