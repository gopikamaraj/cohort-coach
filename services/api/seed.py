# ruff: noqa: E501
"""Copy papers between databases: a one-time seed for a fresh deployment.

`export_papers(db, path)` writes the paper tables to a JSON file. `load_papers(db, path)` inserts them
when the target has no papers yet, so a restart never doubles or overwrites anything. Papers hold the
printed questions and their keys only: no child data, no sheet photo. The startup hook runs only when
`SEED_PAPERS_FILE` is set."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, insert, select
from sqlalchemy.orm import Session

from services.papers.models import PaperEvent, PaperItemRow, PaperRow
from services.papers_hub.models import PaperImport

# parents first, so a foreign key always finds its row
MODELS = (PaperRow, PaperItemRow, PaperImport, PaperEvent)


def _cell(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


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
