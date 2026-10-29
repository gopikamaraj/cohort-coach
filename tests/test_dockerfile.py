"""The API image must hold every file the running code reads. A missing one was a 500 on the live
pilot app (Generate audio) that no test caught, because tests run from the whole repository."""

from __future__ import annotations

from pathlib import Path

from ai.validators.check_items import GOLDEN
from services.api.sprites.palette import SPRITES
from services.pilot.audio import VOICES
from services.pilot.lessons import CONTENT as LESSONS

ROOT = Path(__file__).resolve().parent.parent


def _copied() -> list[str]:
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    return [part for ln in lines if ln.startswith("COPY ") for part in ln.split()[1:-1]]


def test_the_image_copies_every_file_the_pilot_api_reads_at_run_time() -> None:
    copied = [c.rstrip("/") for c in _copied()]
    for needed in (GOLDEN, SPRITES, VOICES, LESSONS):
        rel = needed.relative_to(ROOT).as_posix()
        assert any(rel == c or rel.startswith(c + "/") for c in copied), (
            f"{rel} is not in the image"
        )


def test_dockerignore_does_not_hide_the_golden_forms_from_the_build() -> None:
    """The build context drops docs/; the one file the validator reads must be let back in."""
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    rel = GOLDEN.relative_to(ROOT).as_posix()
    docs_dropped = any(ln.strip().rstrip("/") == "docs" for ln in lines)
    assert not docs_dropped or f"!{rel}" in [ln.strip() for ln in lines]


def test_the_image_installs_ffmpeg_for_the_lesson_audio() -> None:
    """Without it, approving a lesson fails to voice it ("audio:unavailable") on the live server."""
    assert "ffmpeg" in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_the_image_copies_what_the_assistant_reads_at_run_time() -> None:
    """The scope file and the bundled indexes; docs/ is not in the image, so the index carries the
    rubric map, the deck and video facts and the question banks."""
    from services.assistant.index import INDEX_DIR
    from services.assistant.scopes import SCOPES_FILE

    copied = [c.rstrip("/") for c in _copied()]
    for needed in (
        SCOPES_FILE,
        INDEX_DIR / "judge.json",
        INDEX_DIR / "rubric.json",
        INDEX_DIR / "META.json",
    ):
        rel = needed.relative_to(ROOT).as_posix()
        assert any(rel == c or rel.startswith(c + "/") for c in copied), (
            f"{rel} is not in the image"
        )
        assert needed.exists(), f"{rel} is missing: run python scripts/build_assistant_index.py"


def test_the_image_holds_what_the_assistant_reads_at_run_time() -> None:
    """The image copies services/ and not docs/ or the repository root, so the bundled index must
    carry the rubric map, the deck and video facts, the question banks and the scope file."""
    from services.assistant.index import INDEX_DIR

    assert any(c == "services" for c in (x.rstrip("/") for x in _copied()))
    for name in (
        "judge.json",
        "rubric.json",
        "submission.json",
        "questions.json",
        "META.json",
        "assistant_scopes.yaml",
    ):
        assert (INDEX_DIR / name).exists(), (
            f"{name} missing: run python scripts/build_assistant_index.py"
        )
