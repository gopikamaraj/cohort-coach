from __future__ import annotations

import pytest

from ai.config import DEFAULT_MODELS, POLICIES
from ai.pricing import Usage, cost_usd, load_pricing
from ai.prompt_loader import load_prompt
from ai.registry import BY_ID, CALLS, LAYERS, get_call


def test_registry_lists_all_eight_calls_with_all_five_layers() -> None:
    assert [c.id for c in CALLS] == [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13]
    for call in CALLS:
        for layer in LAYERS:
            assert len(call.layers[layer]) > 20, (call.key, layer)


def test_registry_models_come_from_config_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_call(1).model == DEFAULT_MODELS["MODEL_CHILD"] == "claude-sonnet-5-5"
    assert get_call(5).model == "claude-opus-5-5"
    monkeypatch.setenv("MODEL_CHILD", "claude-haiku-5-5")
    assert get_call(1).model == "claude-haiku-5-5"


def test_every_call_has_a_prompt_policy_and_price() -> None:
    models = load_pricing()["models"]
    assert set(POLICIES) == {c.key for c in CALLS}
    for call in CALLS:
        prompt = load_prompt(call.key)
        assert prompt.id == call.key and prompt.version >= 1 and prompt.changelog
        assert prompt.model_env == call.model_env
        assert call.model in models, call.model
        assert BY_ID[call.id] is call


def test_stable_prompts_are_long_enough_to_try_caching() -> None:
    # The cache floor is 512 tokens on these models (DECISIONS.md); about 4 characters a token.
    # The real proof is cache_read_input_tokens > 0 in live logs (checked by run_call).
    for call in CALLS:
        assert len(load_prompt(call.key).body) >= 2000, call.key


def test_live_turn_calls_retry_at_most_once() -> None:
    for call in CALLS:
        if call.live_turn:
            assert POLICIES[call.key].max_retries <= 1


def test_practice_class_calls_log_metadata_only() -> None:
    assert {c.id for c in CALLS if c.metadata_only} == {1, 2, 3, 8, 10}


def test_pricing_has_source_url_and_date() -> None:
    data = load_pricing()
    assert str(data["source_url"]).startswith("https://platform.claude.com/")
    assert str(data["as_of"]).startswith("2026-")


def test_cost_from_usage_uses_the_yaml_prices() -> None:
    usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cache_read_tokens=1_000_000)
    # Sonnet 5.5: 2.00 input + 10.00 output + 0.10 cache read
    assert cost_usd("claude-sonnet-5-5", usage) == pytest.approx(12.10)
    assert cost_usd("claude-sonnet-5-5", usage, batch=True) == pytest.approx(6.05)
    with pytest.raises(KeyError):
        cost_usd("claude-unknown", usage)


def test_thinking_is_spelled_per_model_and_only_switched_off_where_allowed() -> None:
    from ai.config import POLICIES, thinking_param

    off = POLICIES["c07_checker"]
    assert thinking_param("claude-haiku-5-5", off) == {"type": "disabled"}
    assert thinking_param("claude-sonnet-5-5", off) == {"type": "between_tools"}
    assert thinking_param("claude-opus-5-5", off) is None  # Opus 5.5 cannot switch it off
    assert thinking_param("claude-sonnet-5-5", POLICIES["c03_feedback"]) is None  # adaptive
