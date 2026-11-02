"""The cheap evals of the 32-state model stay green: fidelity on the sim_fidelity protocol (bar
100%), and the exemplar replay reproduces the recorded Watch runs under legacy turn for turn."""

from __future__ import annotations

from pathlib import Path

from evals.runners import bayes_fidelity, bayes_replay


def test_bayesian_fidelity_is_200_of_200_with_and_without_the_stage_mix() -> None:
    for stages in (False, True):
        r = bayes_fidelity.run(stages=stages)
        assert r["turns"] == 200 and r["passed"], r["failures"]


def test_the_replay_reproduces_every_recorded_watch_run_under_legacy() -> None:
    runs = sorted(Path(bayes_replay.RUNS).glob("*.json"))
    assert runs
    for path in runs:
        legacy = bayes_replay.replay(path, "legacy")
        done, total = legacy["turns_matching_recorded_engine"].split(" of ")
        assert done == total, path.name
        bayes = bayes_replay.replay(path, "bayesian")
        assert bayes["turns"] == legacy["turns"] and bayes["final_marginals"]
