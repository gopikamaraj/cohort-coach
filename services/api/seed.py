# ruff: noqa: E501
"""Copy papers between databases: a one-time seed for a fresh deployment.

`export_papers(db, path)` writes the paper tables to a JSON file. `load_papers(db, path)` inserts them
when the target has no papers yet, so a restart never doubles or overwrites anything. Papers hold the
printed questions and their keys only: no child data, no sheet photo. The startup hook runs only when
`SEED_PAPERS_FILE` is set."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, insert, select
from sqlalchemy.orm import Session

from services.papers.models import PaperEvent, PaperItemRow, PaperRow
from services.papers_hub.models import PaperImport

# parents first, so a foreign key always finds its row
MODELS = (PaperRow, PaperItemRow, PaperImport, PaperEvent)


def _cell(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (datetime, date)) else value


def export_papers(db: Session, path: Path) -> dict[str, int]:
    out: dict[str, list[dict[str, Any]]] = {}
    for model in MODELS:
        cols = [c.name for c in model.__table__.columns]
        rows = db.execute(select(model.__table__)).mappings().all()
        out[model.__tablename__] = [{c: _cell(r[c]) for c in cols} for r in rows]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: len(v) for k, v in out.items()}


def load_papers(db: Session, path: Path) -> dict[str, int]:
    if db.execute(select(PaperRow.id).limit(1)).first() is not None:
        return {}  # the target already has papers: leave them alone
    data = json.loads(path.read_text(encoding="utf-8"))
    loaded: dict[str, int] = {}
    for model in MODELS:
        table = model.__table__
        stamps = {c.name for c in table.columns if isinstance(c.type, DateTime)}
        rows = [
            {k: (datetime.fromisoformat(v) if k in stamps and isinstance(v, str) else v) for k, v in row.items()}
            for row in data.get(model.__tablename__, [])
        ]
        if rows:
            db.execute(insert(table), rows)
        loaded[model.__tablename__] = len(rows)
    db.commit()
    return loaded


# ---- every table: a copy of one whole database into another (a fresh deployment) -----------------


def _all_tables() -> list[Any]:
    import services.api.profiles  # noqa: F401  (imports every model)
    from services.api.db import Base

    return list(Base.metadata.sorted_tables)  # parents before children


def export_all(db: Session, path: Path) -> dict[str, int]:
    from sqlalchemy import inspect

    insp = inspect(db.get_bind())
    have = set(insp.get_table_names())
    out: dict[str, list[dict[str, Any]]] = {}
    for table in _all_tables():
        if table.name not in have:
            continue
        # an older database may lack newer columns: copy the ones it has, the rest take their defaults
        present = {c["name"] for c in insp.get_columns(table.name)}
        cols = [c for c in table.columns if c.name in present]
        rows = db.execute(select(*cols)).mappings().all()
        out[table.name] = [{c.name: _cell(r[c.name]) for c in cols} for r in rows]
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {k: len(v) for k, v in out.items() if v}


def load_all(db: Session, path: Path) -> dict[str, int]:
    """Fill every table that is empty; a table that already has rows is left alone, so a restart is safe."""
    from sqlalchemy import Date

    data = json.loads(path.read_text(encoding="utf-8"))
    loaded: dict[str, int] = {}
    for table in _all_tables():
        rows = data.get(table.name) or []
        if not rows or db.execute(select(table).limit(1)).first() is not None:
            continue
        stamps = {c.name for c in table.columns if isinstance(c.type, DateTime)}
        days = {c.name for c in table.columns if isinstance(c.type, Date) and not isinstance(c.type, DateTime)}

        def fix(k: str, v: Any, stamps: set[str] = stamps, days: set[str] = days) -> Any:
            if isinstance(v, str) and k in stamps:
                return datetime.fromisoformat(v)
            if isinstance(v, str) and k in days:
                return datetime.fromisoformat(v).date()
            return v

        try:
            for i in range(0, len(rows), 500):
                db.execute(insert(table), [{k: fix(k, v) for k, v in row.items()} for row in rows[i : i + 500]])
            db.commit()
            loaded[table.name] = len(rows)
        except Exception:  # one table that will not take its rows must not stop the others
            db.rollback()
            logging.getLogger("seed").exception("table %s not loaded", table.name)
    return loaded
