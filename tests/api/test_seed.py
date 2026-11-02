"""Papers copied between databases: once, and never over papers already there."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.db import Base, make_engine
from services.api.seed import export_papers, load_papers
from services.papers.models import PaperItemRow, PaperRow


def _db(path: Path) -> Session:
    engine = make_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_a_seed_copies_the_papers_once_and_leaves_existing_ones_alone(tmp_path: Path) -> None:
    src = Path("deploy_seed/papers.json")
    with _db(tmp_path / "a.sqlite") as fresh:
        counts = load_papers(fresh, src)
        assert counts["paper"] >= 1 and counts["paper_item"] >= 1
        n = fresh.scalar(select(func.count()).select_from(PaperRow))
        items = fresh.scalar(select(func.count()).select_from(PaperItemRow))
        assert load_papers(fresh, src) == {}  # a second start adds nothing
        assert fresh.scalar(select(func.count()).select_from(PaperRow)) == n
        out = tmp_path / "again.json"
        assert export_papers(fresh, out)["paper_item"] == items  # what went in comes out unchanged


def test_every_table_is_copied_into_empty_tables_only(tmp_path: Path) -> None:
    from services.api.seed import export_all, load_all

    with _db(tmp_path / "src.sqlite") as src:
        load_papers(src, Path("deploy_seed/papers.json"))
        counts = export_all(src, tmp_path / "all.json")
        assert counts["paper"] == 1
    with _db(tmp_path / "dst.sqlite") as dst:
        loaded = load_all(dst, tmp_path / "all.json")
        assert loaded["paper"] == 1 and loaded["paper_item"] == counts["paper_item"]
        assert load_all(dst, tmp_path / "all.json") == {}  # a table that has rows is left alone
