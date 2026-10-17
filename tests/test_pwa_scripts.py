from __future__ import annotations

import csv
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import bundle_size, i18n

ROOT = Path(__file__).resolve().parents[1]


def make_dist(tmp_path: Path, js_bytes: int) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    # Incompressible content, so the gzip size is close to the raw size.
    (dist / "assets" / "index-abc.js").write_bytes(__import__("os").urandom(js_bytes))
    (dist / "assets" / "lazy.js").write_bytes(b"x" * 5_000_000)  # not initial: never counted
    (dist / "index.html").write_text(
        '<html><head><script type="module" src="/assets/index-abc.js"></script></head></html>',
        encoding="utf-8",
    )
    return dist


def test_bundle_budget_counts_only_initial_scripts_and_gzips_them(tmp_path: Path) -> None:
    total, sizes = bundle_size.check(make_dist(tmp_path, 100_000))
    assert [n for n, _ in sizes] == ["index-abc.js"]
    assert 100_000 <= total <= 101_000


@pytest.mark.parametrize(("size", "code"), [(100_000, 0), (450_000, 0), (1_100_000, 1)])
def test_bundle_budget_passes_warns_and_fails(
    tmp_path: Path, size: int, code: int, capsys: pytest.CaptureFixture[str]
) -> None:
    assert bundle_size.main(["--dist", str(make_dist(tmp_path, size))]) == code
    out = capsys.readouterr().out
    assert ("WARN" in out) == (400_000 < size <= 1_000_000)
    assert ("FAIL" in out) == (code == 1)


def test_the_built_app_is_under_the_budget() -> None:
    dist = ROOT / "apps" / "pwa" / "dist"
    if not (dist / "index.html").exists():
        pytest.skip("the PWA has not been built here (npm run build)")
    total, _ = bundle_size.check(dist)
    assert total < bundle_size.FAIL_BYTES


def test_gzip_is_what_is_measured(tmp_path: Path) -> None:
    f = tmp_path / "a.js"
    f.write_bytes(b"hello " * 10_000)
    assert bundle_size.compressed_size(f) == len(gzip.compress(f.read_bytes(), compresslevel=9))


def test_i18n_csv_round_trips_and_the_todo_is_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "i18n"
    shutil.copytree(i18n.I18N, work)
    monkeypatch.setattr(i18n, "I18N", work)  # the import writes into a copy, never the real files
    out = tmp_path / "strings.csv"
    assert i18n.export(out) == 0
    with out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    en = json.loads((i18n.I18N / "en.json").read_text(encoding="utf-8"))
    assert [r["key"] for r in rows] == list(en) and all(
        r["en"] and r["hi"] and r["ta"] for r in rows
    )
    before = {lang: (i18n.I18N / f"{lang}.json").read_text(encoding="utf-8") for lang in i18n.LANGS}
    assert i18n.import_csv(out) == 0  # importing what was exported changes nothing
    after = {lang: (i18n.I18N / f"{lang}.json").read_text(encoding="utf-8") for lang in i18n.LANGS}
    assert after == before
    done = subprocess.run(
        [sys.executable, "scripts/i18n.py", "todo", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stdout


def test_a_missing_translation_is_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    real = i18n.load()
    real["hi"]["common.back"] = ""
    monkeypatch.setattr(i18n, "load", lambda: real)
    assert "`common.back` | hi" in i18n.todo_text()
