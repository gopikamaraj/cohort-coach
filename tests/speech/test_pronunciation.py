from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from services.speech import pronunciation as pr


def test_drafts_are_empty_so_nothing_is_guessed() -> None:
    for lang in ("hi", "ta"):
        assert pr.load(lang) == {}
        assert pr.dictionary_json(lang) is None


def test_filled_words_become_a_dictionary_and_blank_ones_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "hi.yaml").write_text(
        yaml.safe_dump(
            {"language": "hi-IN", "words": [{"word": "a", "say": "ay"}, {"word": "b", "say": ""}]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pr, "DIR", tmp_path)
    assert json.loads(pr.dictionary_json("hi") or "") == {"pronunciations": {"hi-IN": {"a": "ay"}}}


def test_too_many_words_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    words = [{"word": f"w{i}", "say": "x"} for i in range(pr.MAX_WORDS + 1)]
    (tmp_path / "ta.yaml").write_text(
        yaml.safe_dump({"language": "ta-IN", "words": words}), encoding="utf-8"
    )
    monkeypatch.setattr(pr, "DIR", tmp_path)
    with pytest.raises(ValueError):
        pr.dictionary_json("ta")
