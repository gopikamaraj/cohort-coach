"""No test here may call a model: making a module runs call 18, so it is off here unless the test
is about it (test_narration.py fakes the call itself)."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_narration_call(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.module.__name__.endswith("test_narration"):
        return
    from services.modules import narration

    monkeypatch.setattr(narration, "run", lambda *a, **k: None)
