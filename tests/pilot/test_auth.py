"""Pilot sign-in: accounts from the environment, signed expiring tokens, role permissions."""

from __future__ import annotations

from services.pilot import auth
from tests.pilot.conftest import Env, init_body, photo


def signin(env: Env, name: str, key: str):  # type: ignore[no-untyped-def]
    return env.client.post("/api/pilot/auth/signin", json={"name": name, "key": key})


def test_a_known_account_signs_in_and_learns_its_roles(env: Env) -> None:
    res = signin(env, "seema", "seema-key")
    assert res.status_code == 200
    assert res.json()["roles"] == ["coordinator", "coach"]
    me = env.client.get("/api/pilot/auth/me", headers=env.h("seema")).json()
    assert "pilot.upload_sheets" in me["can"] and "pilot.approve_audio" in me["can"]


def test_a_wrong_key_or_unknown_name_is_refused_the_same_way(env: Env) -> None:
    a = signin(env, "seema", "nope")
    b = signin(env, "nobody", "nope")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_five_wrong_tries_pause_the_name(env: Env) -> None:
    for _ in range(5):
        assert signin(env, "ops", "bad").status_code == 401
    assert signin(env, "ops", "ops-key").status_code == 429
    env.clock.now += 11 * 60
    assert signin(env, "ops", "ops-key").status_code == 200


def test_tokens_expire(env: Env) -> None:
    headers = env.h("ops")
    assert env.client.get("/api/pilot/config", headers=headers).status_code == 200
    env.clock.now += auth.TOKEN_TTL_S + 1
    assert env.client.get("/api/pilot/config", headers=headers).status_code == 401


def test_a_forged_or_edited_token_is_refused(env: Env) -> None:
    token = env.h("ops")["Authorization"].split()[1]
    body, _, sig = token.partition(".")
    for bad in (f"{body}.{sig[:-2]}xx", f"x{body}.{sig}", "garbage", ""):
        res = env.client.get("/api/pilot/config", headers={"Authorization": f"Bearer {bad}"})
        assert res.status_code == 401


def test_removing_an_account_ends_its_tokens(env: Env, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    headers = env.h("ops")
    monkeypatch.setenv("PILOT_ACCOUNTS", "seema:coordinator+coach:seema-key")
    assert env.client.get("/api/pilot/config", headers=headers).status_code == 401


def test_without_a_secret_sign_in_is_off_not_open(env: Env, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("PILOT_TOKEN_SECRET")
    monkeypatch.delenv("LINK_SECRET", raising=False)
    assert signin(env, "ops", "ops-key").status_code == 503


def test_each_role_can_do_only_its_own_things(env: Env) -> None:
    data = photo(1)
    # the coordinator uploads; the coach and the officer do not
    assert (
        env.client.post(
            "/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops")
        ).status_code
        == 200
    )
    for who in ("rev", "off"):
        res = env.client.post("/api/pilot/sheets/init", json=init_body(data), headers=env.h(who))
        assert res.status_code == 403, who
    # the coach and the officer can look at the audio page; only the coach can approve
    for who in ("rev", "off", "ops"):
        assert env.client.get("/api/pilot/audio", headers=env.h(who)).status_code == 200, who
    assert env.client.post("/api/pilot/audio/x/approve", headers=env.h("ops")).status_code == 403
    assert env.client.post("/api/pilot/audio/x/approve", headers=env.h("off")).status_code == 403
    assert env.client.post("/api/pilot/audio/x/approve", headers=env.h("rev")).status_code == 404
    # the officer cannot generate or change settings
    assert (
        env.client.put(
            "/api/pilot/config/audio-count", json={"audio_count": 2}, headers=env.h("off")
        ).status_code
        == 403
    )
