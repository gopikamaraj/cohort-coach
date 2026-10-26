"""P09 T07: the rejection loop. A rejection waits in pending; "use as checker example" promotes it
to approved; the next call 7 prompt contains it; the audit row records which example set call 7
saw."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from sqlalchemy.orm import sessionmaker

from ai.audit import SqlAuditSink
from ai.calls.c07_checker import check_output
from ai.client import CallContext
from ai.guard import rejections as guard
from ai.schemas import Verdict
from services.api.db import AiCall, Base, make_engine
from services.content import rejections
from tests.support_ai import FakeClient

PASS = Verdict(passed=True, reason_short="ok", reason_for_user="ok")


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    pending, approved = tmp_path / "pending", tmp_path / "approved"
    monkeypatch.setattr(rejections, "PENDING_DIR", pending)
    monkeypatch.setattr(guard, "APPROVED_DIR", approved)
    return pending, approved


def pend(pending: Path, text: str = "Say 52 - 29 = 37, so it is 37.") -> Path:
    return rejections.write_pending(
        text, "wrong_maths", "en", item_id="abc", note="n", directory=pending, date="2026-10-26"
    )


def test_a_pending_rejection_does_not_reach_the_checker(dirs: tuple[Path, Path]) -> None:
    pending, _ = dirs
    pend(pending)
    assert guard.examples_block() == ""  # nothing promoted yet


def test_promoting_moves_it_to_approved_and_into_the_checker_prompt(
    dirs: tuple[Path, Path],
) -> None:
    pending, approved = dirs
    path = pend(pending)
    saved = rejections.promote(path)
    assert not path.exists() and saved.parent == approved
    block = guard.examples_block()
    assert (
        "Rejected before, and why" in block and "wrong_maths" in block and "52 - 29 = 37" in block
    )


def test_the_curator_can_trim_the_excerpt_when_promoting(dirs: tuple[Path, Path]) -> None:
    pending, _ = dirs
    path = pend(pending, "A long script. Say 52 - 29 = 37, so it is 37. More script.")
    saved = rejections.promote(path, text="Say 52 - 29 = 37, so it is 37.")
    assert (
        yaml.safe_load(saved.read_text(encoding="utf-8"))["text"]
        == "Say 52 - 29 = 37, so it is 37."
    )


def test_a_file_with_a_bad_reason_cannot_be_promoted(dirs: tuple[Path, Path]) -> None:
    pending, _ = dirs
    path = pend(pending)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["reason"] = "meh"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        rejections.promote(path)
    assert path.exists()


def test_a_discarded_rejection_never_becomes_an_example(dirs: tuple[Path, Path]) -> None:
    pending, _ = dirs
    path = pend(pending)
    rejections.discard(path)
    assert not path.exists() and guard.examples_block() == ""


def test_the_name_must_look_like_one_of_our_files(dirs: tuple[Path, Path]) -> None:
    pending, _ = dirs
    pend(pending)
    assert rejections.find_pending("2026-10-26-001").name == "2026-10-26-001.yaml"
    for bad in ("../secrets", "2026-10-26-001.yaml", "x/y", ""):
        with pytest.raises(ValueError):
            rejections.find_pending(bad)


@pytest.fixture
def sink(tmp_path: Path) -> Iterator[SqlAuditSink]:
    engine = make_engine(f"sqlite:///{tmp_path / 'audit.sqlite'}")
    Base.metadata.create_all(engine)
    yield SqlAuditSink(sessionmaker(engine, expire_on_commit=False))


def run_check(sink: SqlAuditSink) -> tuple[FakeClient, int]:
    client = FakeClient([PASS])
    ctx = CallContext(mode="stub", client=client, sink=sink)  # type: ignore[arg-type]
    out = check_output(
        "Ask her how she got it.",
        audience="teacher",
        language="en",
        target_error="SUB-SFL",
        code_checks=[],
        context=ctx,
    )
    return client, out.result.audit_id


def test_the_next_call_7_prompt_contains_the_promoted_example(
    dirs: tuple[Path, Path], sink: SqlAuditSink
) -> None:
    pending, _ = dirs
    rejections.promote(pend(pending))
    client, _ = run_check(sink)
    system = " ".join(b["text"] for b in client.messages.calls[-1]["system"])
    assert "Rejected before, and why" in system and "52 - 29 = 37" in system


def test_the_audit_row_records_the_example_set_version(
    dirs: tuple[Path, Path], sink: SqlAuditSink
) -> None:
    pending, _ = dirs
    _, first = run_check(sink)
    rejections.promote(pend(pending))
    _, second = run_check(sink)
    rows = {r.id: r for r in sink.recent(10)}

    def recorded(row: AiCall) -> tuple[str, str]:
        entry = next(v for v in row.validator_results if v["name"] == "checker_examples")
        return entry["codes"][0], entry["codes"][1]

    assert recorded(rows[first]) == ("none", "0")
    version, count = recorded(rows[second])
    assert count == "1" and version == guard.examples_version() and version != "none"
    assert len(version) == 8
