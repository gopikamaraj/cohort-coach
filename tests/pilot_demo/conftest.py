"""A FAKE pilot folder made from the synthetic demo sheets. Never real data."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image, ImageFilter

from services.demo import scenario, sheets
from tests.demo.test_sheets import one

MANIFEST = """\
consent:
  consent_confirmed: true
  confirmed_by: Test Person
  date: 2026-10-20
  scope: internal demo and the project video
test:
  name: Pilot pre-test
  form: A
  kind: pre
  date: 2026-10-23
classes:
  - class_code: 3A
    strength: 5
    teacher_label: T1
    test_date: 2026-10-23
    no_sheet: [5]
    absent: [4]
  - class_code: 3B
    strength: 3
    teacher_label: T2
    test_date: 2026-10-23
    dictation: {1: 453, 2: 618}
"""


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory: pytest.TempPathFactory) -> dict[int, bytes]:
    """Three synthetic sheets (rolls 1 to 3), drawn by code. A cheap stand-in for the camera."""
    mp = pytest.MonkeyPatch()
    mp.setattr(sheets, "photograph", lambda img, child, seed: img.resize((620, 877)))
    try:
        tmp = tmp_path_factory.mktemp("synthetic")
        return {r: one(tmp, r) for r in (1, 2, 3)}
    finally:
        mp.undo()


def truth_rows() -> dict[int, list[str]]:
    demo = scenario.build_class(scenario.load_scenario())
    return {r: list(demo.children[r - 1].answers) for r in (1, 2, 3)}


def png_to_jpeg_bytes(data: bytes, rotate: int = 0, blur: float = 0.0, ext: str = "PNG") -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if rotate:
        img = img.rotate(rotate, expand=True)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    img.save(buf, ext)
    return buf.getvalue()


@pytest.fixture
def folder(tmp_path: Path, synthetic: dict[int, bytes]) -> Iterator[Path]:
    root = tmp_path / "pilot"
    (root / "raw").mkdir(parents=True)
    (root / "truth").mkdir()
    (root / "manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    raw = root / "raw"
    (raw / "3A-roll01.png").write_bytes(synthetic[1])
    (raw / "copy of 3A-roll01.png").write_bytes(synthetic[1])  # identical bytes
    (raw / "3A-roll01 blurry.png").write_bytes(png_to_jpeg_bytes(synthetic[1], blur=3.0))
    (raw / "3A_roll_02.png").write_bytes(png_to_jpeg_bytes(synthetic[2], rotate=90))  # on its side
    (raw / "IMG_0003.png").write_bytes(synthetic[3])  # no class or roll in the name
    rows = truth_rows()
    header = "roll," + ",".join(f"q{i}" for i in range(1, 11))
    (root / "truth" / "3A.csv").write_text(
        header + "\n" + "\n".join(f"{r}," + ",".join(rows[r]) for r in (1, 2)) + "\n",
        encoding="utf-8",
    )
    yield root
