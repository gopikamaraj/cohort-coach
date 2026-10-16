import json
import subprocess
import sys
from pathlib import Path

from scripts.evidence import build_all

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"


def test_demo_verdict_table_is_labelled_simulated_and_sourced() -> None:
    files = build_all()
    md = files["demo_verdicts.md"]
    assert "SIMULATED" in md.splitlines()[2] or "simulated" in md.lower()
    assert "data/synthetic/block_T1T2.json" in md and "data hash" in md
    assert "SUB-SFL v1" in md and "SUB-NODEC v1" in md
    data = json.loads(files["demo_verdicts.json"])
    assert data["SUB-SFL v1"]["verdict"] == "working"
    assert data["SUB-NODEC v1"]["verdict"] == "not_working"


def test_figures_covering_fewer_than_5_classes_are_hidden_in_the_table() -> None:
    files = build_all()
    row = next(line for line in files["demo_verdicts.md"].splitlines() if "PV-HEARD v1" in line)
    assert "hidden" in row
    data = json.loads(files["demo_verdicts.json"])
    assert data["PV-HEARD v1"]["hidden"] is True and data["PV-HEARD v1"]["estimate_points"] is None


def test_small_samples_carry_a_confidence_note() -> None:
    md = build_all()["demo_verdicts.md"]
    row = next(line for line in md.splitlines() if "ADD-NOCARRY v1" in line)
    assert "read as directional" in row


def test_eval_summary_comes_from_the_results_files() -> None:
    md = build_all()["eval_summary.md"]
    stats = json.loads((ROOT / "evals/results/statistics.json").read_text(encoding="utf-8"))
    items = json.loads((ROOT / "evals/results/engine_items.json").read_text(encoding="utf-8"))
    assert f"{stats['recovery']:.0%}" in md and f"{stats['false_working']:.0%}" in md
    assert "evals/results/statistics.json" in md and "evals/results/engine_items.json" in md
    assert str(items["problems_per_error"]) in md


def test_numbers_registry_lists_every_generated_file_with_source_and_sample() -> None:
    files = build_all()
    registry = files["numbers.md"]
    for name in ("demo_verdicts.md", "eval_summary.md"):
        assert name in registry
    assert "Sample" in registry and "Source" in registry


def test_committed_evidence_is_not_stale() -> None:
    for name, text in build_all().items():
        assert (EVIDENCE / name).read_text(encoding="utf-8") == text, name


def test_evidence_command_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tasks.py"), "evidence", "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout
    assert "STALE" not in result.stdout
