"""The index holds only allowlisted files, and anything personal or secret fails the build."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from services.assistant import index

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "deny": ["**/.env*", "data/**", "docs/evidence/**", "**/*.png"],
    "namespaces": {
        "judge": {"kind": "markdown", "files": ["README.md", "docs/*.md"]},
        "judge_deck": {"into": "judge", "kind": "slides", "files": ["docs/submission/slides.md"]},
        "judge_video": {
            "into": "judge",
            "kind": "video",
            "files": ["docs/submission/video_script.md"],
        },
        "product_help": {"kind": "markdown", "files": ["docs/help/product.md"]},
    },
}


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(
        tmp_path, "README.md", "# Title\n\nCohort Coach groups teachers. It never names a child.\n"
    )
    write(tmp_path, "docs/a.md", "# A\n\n## Offline\n\nThe check queues offline. Lessons replay.\n")
    write(tmp_path, "docs/help/product.md", "# Help\n\nTap Home to start.\n")
    write(
        tmp_path,
        "docs/submission/slides.md",
        "# Deck\n\n## Slide 1: Title\n\nCohort Coach.\n\n## Slide 2: Problem\n\nTraining is generic. Rarely practised.\n",
    )
    write(
        tmp_path,
        "docs/submission/video_script.md",
        "# Script\n\n[00:00-00:15] Problem: Training is generic.\n[00:15-00:35] Idea: Group by mistake.\n",
    )
    return tmp_path


def test_only_allowlisted_files_are_read(repo: Path) -> None:
    # Files outside the allowlist hold secrets and are never opened, so the build still passes.
    write(repo, ".env.md", "ANTHROPIC_API_KEY=sk-ant-" + "a" * 40)
    write(repo, "data/pilot.md", "Roll no 12 phone 9876543210")
    write(repo, "docs/evidence/x.md", "teacher@school.org")
    write(repo, "notes/private.md", "9876543210")
    (repo / "docs/photo.png").write_bytes(b"\x89PNG")
    built = index.build(repo, SOURCES)
    paths = {c.path for cs in built.chunks.values() for c in cs}
    assert paths == {
        "README.md",
        "docs/a.md",
        "docs/help/product.md",
        "docs/submission/slides.md",
        "docs/submission/video_script.md",
    }
    assert "docs/help/product.md" not in {
        c.path for c in built.chunks["judge"]
    }  # namespaces stay apart


@pytest.mark.parametrize(
    ("planted", "kind"),
    [
        ("Contact me at teacher.name@gmail.com for details.", "email"),
        ("Call 9876543210 after school.", "phone"),
        ("Call +91 98765 43210? no: +91-9876543210 works.", "phone"),
        ("The sheet of Roll no 14 was unclear.", "roll number"),
        ("Use key sk-ant-api03-" + "x" * 30 + " for the demo.", "secret"),
        ("api_key = " + "A1b2C3d4" * 3, "secret"),
        ("-----BEGIN RSA PRIVATE KEY-----", "secret"),
    ],
)
def test_a_planted_secret_or_personal_detail_fails_the_build(
    repo: Path, planted: str, kind: str
) -> None:
    write(repo, "docs/a.md", f"# A\n\nFine line.\n\n{planted}\n")
    with pytest.raises(index.IndexBuildError) as e:
        index.build(repo, SOURCES)
    msg = str(e.value)
    assert f"docs/a.md:5 {kind}" in msg
    for value in ("teacher.name", "9876543210", "98765", "sk-ant", "A1b2C3d4", "PRIVATE KEY"):
        assert value not in msg  # the message names the place and the kind, never the value


def test_obvious_placeholders_and_service_accounts_are_not_personal(repo: Path) -> None:
    write(
        repo,
        "docs/a.md",
        "# A\n\nWrite to you@example.com. The API runs as svc@my-proj.iam.gserviceaccount.com.\n",
    )
    index.build(repo, SOURCES)


def test_chunks_have_stable_unique_ids_and_the_right_metadata(repo: Path) -> None:
    a = index.build(repo, SOURCES)
    b = index.build(repo, SOURCES)
    assert [c.id for cs in a.chunks.values() for c in cs] == [
        c.id for cs in b.chunks.values() for c in cs
    ]
    judge = {c.id: c for c in a.chunks["judge"]}
    off = next(c for c in judge.values() if c.heading == "A > Offline")
    assert off.line == 5 and "queues offline" in off.text and off.kind == "file"
    s2 = judge["judge:docs/submission/slides.md#slide-2"]
    assert (s2.kind, s2.slide_no, s2.heading) == ("slide", 2, "Slide 2: Problem")
    v = judge["judge:docs/submission/video_script.md#t-00:15"]
    assert (v.kind, v.ts_start, v.ts_end, v.section) == ("video", 15, 35, "Idea")


def test_a_long_section_is_cut_by_sentence_not_mid_sentence(repo: Path) -> None:
    sentences = [
        f"Sentence number {i} says something about training and practice." for i in range(40)
    ]
    write(repo, "docs/a.md", "# A\n\n" + " ".join(sentences) + "\n")
    chunks = [c for c in index.build(repo, SOURCES).chunks["judge"] if c.path == "docs/a.md"]
    assert len(chunks) > 1
    assert all(c.text.rstrip().endswith(".") for c in chunks)
    assert all(index.words(c.text) <= index.CHUNK_WORDS + 12 for c in chunks)


def test_a_table_row_is_one_unit_and_the_divider_row_is_dropped(repo: Path) -> None:
    write(repo, "docs/a.md", "# A\n\n| Id | Claim |\n| --- | --- |\n| 1 | Offline works |\n")
    text = " ".join(
        c.text for c in index.build(repo, SOURCES).chunks["judge"] if c.path == "docs/a.md"
    )
    assert "Offline works" in text and "---" not in text


def test_the_written_index_records_the_commit_it_was_built_from(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    index.write(index.build(repo, SOURCES), out, sha="abc123")
    assert json.loads((out / "META.json").read_text())["source_commit"] == "abc123"
    assert (out / "judge.json").exists() and (out / "product_help.json").exists()


def test_staleness_check_on_a_fixture_repo(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "sources.yaml"
    src.write_text(yaml.safe_dump(SOURCES), encoding="utf-8")
    monkeypatch.setattr(index, "SOURCES", src)
    out = tmp_path / "out"
    index.write(index.build(repo), out)
    assert index.is_current(out, repo)
    write(repo, "docs/a.md", "# A\n\nChanged.\n")
    assert not index.is_current(out, repo)


def test_the_real_repository_builds_clean_and_the_bundled_index_is_current() -> None:
    built = index.build()
    assert sum(len(c) for c in built.chunks.values()) > 0
    assert index.is_current(), "run: python scripts/build_assistant_index.py"
    spec = index.load_sources()
    for chunks in built.chunks.values():
        for c in chunks:
            assert not index._denied(c.path, spec["deny"]), c.path
            assert c.path.endswith(".md")
            assert ".env" not in c.path and not c.path.startswith("data/")
    assert not any(
        c.path.startswith("docs/help/")
        for c in built.chunks["judge"]
        if c.path != "docs/help/judge.md"
    )
