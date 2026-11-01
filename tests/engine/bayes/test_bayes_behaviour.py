"""Behaviour tests B1 to B8 (docs/BAYESIAN-MODEL.md 7.4), each over at least 200 seeds. The
measurements live in evals/runners/bayes_behaviour.py; the thresholds are fixed in the spec and are
not changed here."""

from __future__ import annotations

import pytest

from evals.runners import bayes_behaviour


@pytest.mark.parametrize("name", list(bayes_behaviour.ALL))
def test_behaviour(name: str) -> None:
    result = bayes_behaviour.ALL[name]()
    seeds = result.get("seeds", result.get("child_turns", 0))
    assert seeds >= 200
    assert result["pass"], result
