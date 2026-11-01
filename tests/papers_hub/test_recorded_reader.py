"""The recorded reader the browser tests rely on: it answers the fixture PDF, and only while the
prompt version it was made for is the current one."""

from __future__ import annotations

import base64
from pathlib import Path

from ai.client import CallContext, CallInput, run_call
from ai.schemas import PaperRead
from services.papers_hub import service as svc

PDF = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "pwa"
    / "e2e"
    / "fixtures"
    / "paper-to-import.pdf"
)


def test_the_fixture_pdf_is_read_from_the_recording_and_stays_in_step_with_the_prompt() -> None:
    jpeg = svc.render_pages([("paper-to-import.pdf", PDF.read_bytes())])[0][1]
    run = run_call(
        16,
        CallInput(trusted={}, images=[("image/jpeg", base64.b64encode(jpeg).decode())]),
        context=CallContext(mode="recorded"),
    )
    assert run.ok and isinstance(run.output, PaperRead), "run scripts/make_paper_import_fixture.py"
    assert [i.n for i in run.output.items][:3] == [1, 2, 3] and run.output.items[
        -1
    ].operation == "other"
    assert not run.fallback_used
