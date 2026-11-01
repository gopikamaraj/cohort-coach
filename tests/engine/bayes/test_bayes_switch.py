"""The switch between the two child models (engine/sim_switch.py) and the contract both keep
(docs/BAYESIAN-MODEL.md section 7, "split and contract")."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine import sim_switch
from engine.bayes.planner import BayesState
from engine.simulator import SessionState, TurnPlan
from services.practice.content import load_scenario
from tests.engine.legacy_golden import FIXTURE, capture, seats_for

ROOT = Path(__file__).resolve().parents[3]
SFL = load_scenario("SUB-SFL")


def test_unset_or_empty_or_legacy_means_legacy_and_bayesian_means_bayesian() -> None:
    assert sim_switch.model_name({}) == "legacy"
    assert sim_switch.model_name({"SIMULATOR_MODEL": ""}) == "legacy"
    assert sim_switch.model_name({"SIMULATOR_MODEL": "legacy"}) == "legacy"
    assert sim_switch.model_name({"SIMULATOR_MODEL": "bayesian"}) == "bayesian"
    seats = seats_for("SUB-SFL")
    assert isinstance(sim_switch.new_session(SFL.config, seats, 5, environ={}), SessionState)
    st = sim_switch.new_session(SFL.config, seats, 5, environ={"SIMULATOR_MODEL": "bayesian"})
    assert isinstance(st, BayesState)


@pytest.mark.parametrize("value", ["bayes", "Bayesian", "rules", "32"])
def test_an_invalid_value_stops_the_api_at_startup_with_a_clear_message(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.api.main import create_app

    monkeypatch.setenv("SIMULATOR_MODEL", value)
    with pytest.raises(ValueError, match="SIMULATOR_MODEL must be legacy or bayesian"):
        create_app()


def test_a_bad_params_file_stops_startup_in_bayesian_mode_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.api.main import create_app

    good = (ROOT / "content" / "bayes" / "params.v1.yaml").read_text(encoding="utf-8")
    bad = tmp_path / "bad.yaml"
    bad.write_text(good.replace("default: 0.85", "default: 1.85"), encoding="utf-8")
    missing = tmp_path / "missing.yaml"
    missing.write_text(good.replace("  tau:", "  not_tau:"), encoding="utf-8")
    for path, why in ((bad, "r_diag"), (missing, "tau"), (tmp_path / "nope.yaml", "cannot read")):
        monkeypatch.setenv("BAYES_PARAMS", str(path))
        monkeypatch.delenv("SIMULATOR_MODEL", raising=False)
        create_app()  # legacy: the parameter file is not read
        monkeypatch.setenv("SIMULATOR_MODEL", "legacy")
        create_app()
        monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
        with pytest.raises(ValueError, match=why):
            create_app()
    monkeypatch.delenv("BAYES_PARAMS")
    create_app()  # bayesian with the default file starts


def test_a_session_keeps_its_model_after_the_environment_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.practice.session import start_session

    monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
    s = start_session("SUB-SFL", "en", seed=5)
    monkeypatch.setenv("SIMULATOR_MODEL", "legacy")
    state = s.state
    for _ in range(4):
        _, state, trace = sim_switch.plan_turn(
            state, s.loaded.config, "show_bundles", addressed=None, posed=None
        )
        assert isinstance(state, BayesState) and trace is not None
    monkeypatch.delenv("SIMULATOR_MODEL")
    legacy = start_session("SUB-SFL", "en", seed=5)
    monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
    _, lstate, ltrace = sim_switch.plan_turn(
        legacy.state, legacy.loaded.config, "show_bundles", addressed=None, posed=None
    )
    assert isinstance(lstate, SessionState) and ltrace is None and legacy.model == "legacy"
    assert s.model == "bayesian"


def test_the_legacy_path_never_imports_engine_bayes() -> None:
    code = (
        "import sys\n"
        "from services.practice.session import start_session\n"
        "from engine import sim_switch\n"
        "s = start_session('SUB-SFL', 'en', seed=5)\n"
        "for m in ('pose_problem', 'show_bundles', 'check_back'):\n"
        "    _, s.state, _ = sim_switch.plan_turn(s.state, s.loaded.config, m,"
        " addressed=None, posed=None)\n"
        "assert not [k for k in sys.modules if k.startswith('engine.bayes')], 'imported'\n"
        "print('ok')\n"
    )
    env = {k: v for k, v in __import__("os").environ.items() if k != "SIMULATOR_MODEL"}
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True
    )
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr
    for path in ("engine/simulator.py", "engine/child_model.py"):
        assert "engine.bayes" not in (ROOT / path).read_text(encoding="utf-8")


def _factory_start(error: str, seed: int) -> object:
    return sim_switch.new_session(load_scenario(error).config, seats_for(error), seed)


def _factory_step(state: object, error: str, move: str, to: str | None) -> tuple[TurnPlan, object]:
    plan, nxt, _ = sim_switch.plan_turn(
        state, load_scenario(error).config, move, addressed=to, posed=None
    )
    return plan, nxt


@pytest.mark.parametrize("setting", [None, "legacy"])
def test_legacy_through_the_factory_is_identical_to_the_golden_runs(
    setting: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if setting is None:
        monkeypatch.delenv("SIMULATOR_MODEL", raising=False)
    else:
        monkeypatch.setenv("SIMULATOR_MODEL", setting)
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    now = json.loads(json.dumps(capture(_factory_start, _factory_step)))
    assert now == saved


def _plan_shape(p: TurnPlan) -> dict[str, str]:
    return {f.name: type(getattr(p, f.name)).__name__ for f in dataclasses.fields(p)}


def test_both_models_return_the_same_plan_fields_and_types() -> None:
    seats = seats_for("SUB-SFL")
    cfg = SFL.config
    leg = sim_switch.new_session(cfg, seats, 5, model="legacy")
    bay = sim_switch.new_session(cfg, seats, 5, model="bayesian")
    assert [c.name for c in leg.children] == [c.name for c in bay.children]
    assert [(c.error, c.stage, c.shy) for c in leg.children] == [
        (c.error, c.stage, c.shy) for c in bay.children
    ]
    for move, to in (("pose_problem", 1), ("ask_explain", 1), ("show_bundles", None)):
        name = leg.children[to].name if to is not None else None
        lp, leg, _ = sim_switch.plan_turn(leg, cfg, move, addressed=name, posed=None)
        bp, bay, trace = sim_switch.plan_turn(bay, cfg, move, addressed=name, posed=None)
        assert set(dataclasses.fields(lp)) == set(dataclasses.fields(bp))
        for f in dataclasses.fields(lp):
            lv, bv = getattr(lp, f.name), getattr(bp, f.name)
            if lv is not None and bv is not None:
                assert type(lv) is type(bv), f.name
        assert bp.trace == ()  # the bayesian extras go to the debug trace, not the plan
        assert trace and "children" in trace
    for lc, bc in zip(leg.children, bay.children, strict=True):
        assert type(lc) is type(bc)
        assert isinstance(bc.strength, float) and isinstance(bc.engagement, float)


def test_bayesian_session_state_round_trips_through_json() -> None:
    seats = seats_for("SUB-NODEC")
    cfg = load_scenario("SUB-NODEC").config
    st = sim_switch.new_session(cfg, seats, 11, model="bayesian", note_tags=["pv_shaky"])
    for move in ("pose_problem", "show_bundles", "tell_rule", "scold", "pose_problem"):
        _, st, _ = sim_switch.plan_turn(st, cfg, move, addressed=None, posed=None)
    data = json.loads(json.dumps(sim_switch.state_to_dict(st)))
    assert data["model"] == "bayesian" and len(data["seats"][1]["belief"]) == 32
    assert data["axes"]["axes"] == ["place_value", "exchange", "written_step", "habit"]
    assert sim_switch.state_from_dict(data) == st
    leg = sim_switch.new_session(cfg, seats, 11, model="legacy")
    assert sim_switch.state_from_dict(json.loads(json.dumps(sim_switch.state_to_dict(leg)))) == leg


def test_note_tags_are_a_closed_list_and_need_the_bayesian_model() -> None:
    seats = seats_for("SUB-SFL")
    with pytest.raises(ValueError, match="need SIMULATOR_MODEL=bayesian"):
        sim_switch.new_session(SFL.config, seats, 5, model="legacy", note_tags=["pv_secure"])
    with pytest.raises(ValueError, match="unknown note tags"):
        sim_switch.new_session(SFL.config, seats, 5, model="bayesian", note_tags=["she is great"])
    st = sim_switch.new_session(SFL.config, seats, 5, model="bayesian", note_tags=["pv_secure"])
    assert st.note_tags == ("pv_secure",)
