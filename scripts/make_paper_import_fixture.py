"""Make the PDF the browser tests upload, and the replay file the reader answers it with.

    python scripts/make_paper_import_fixture.py

The PDF is a plain page (the content does not matter: the reader is replayed, not called). The
replay file is AUTHORED for tests, not a live recording: it holds what a reader would say about a
Grade 3 paper of ten items, and says so in its `note`. It is keyed by the hash of the rendered page
and the prompt version, so a prompt change makes the test fail until this is run again.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from ai.client import CallInput, fixture_path, input_hash  # noqa: E402
from ai.config import model_for  # noqa: E402
from ai.prompt_loader import load_prompt  # noqa: E402
from ai.registry import get_call  # noqa: E402
from services.papers_hub import service as svc  # noqa: E402

PDF = ROOT / "apps" / "pwa" / "e2e" / "fixtures" / "paper-to-import.pdf"

ITEMS = [
    {"n": 1, "operation": "dictate"},
    {"n": 2, "operation": "dictate"},
    {"n": 3, "operation": "add", "a": 38, "b": 47},
    {"n": 4, "operation": "add", "a": 46, "b": 28},
    {"n": 5, "operation": "add", "a": 59, "b": 23},
    {"n": 6, "operation": "subtract", "a": 87, "b": 52},
    {"n": 7, "operation": "subtract", "a": 74, "b": 36},
    {"n": 8, "operation": "subtract", "a": 45, "b": 19},
    {"n": 9, "operation": "subtract", "a": 82, "b": 39},
    {"n": 10, "operation": "subtract", "a": 81, "b": 27, "unsure": True},
    {
        "n": 11,
        "operation": "other",
        "prompt_text": "A rope is 12 m long. Half is cut. How long is the piece?",
    },
]


def main() -> int:
    PDF.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (595, 842), "white")
    ImageDraw.Draw(img).text((40, 40), "Maths questions (a test page)", fill="black")
    img.save(PDF, "PDF")
    jpeg = svc.render_pages([("paper-to-import.pdf", PDF.read_bytes())])[0][1]
    spec = get_call(16)
    inp = CallInput(trusted={}, images=[("image/jpeg", base64.b64encode(jpeg).decode())])
    digest = input_hash(spec, load_prompt(spec.key), model_for(spec.model_env), inp)
    out = fixture_path(spec, digest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "call": spec.key,
                "model": model_for(spec.model_env),
                "prompt_version": load_prompt(spec.key).version,
                "note": "Authored for tests, not a live recording. "
                "Rebuild with scripts/make_paper_import_fixture.py.",
                "outputs": [
                    {
                        "form_letter": "A",
                        "check_code": "A · PRE · 3B · T1",
                        "class_code": "3B",
                        "language": "en",
                        "contains_handwritten_answers": False,
                        "items": ITEMS,
                    }
                ],
                "usage": {
                    "input_tokens": 1500,
                    "output_tokens": 300,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                },
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote {PDF.relative_to(ROOT)} and {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
