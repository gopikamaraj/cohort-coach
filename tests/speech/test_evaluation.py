"""Speech evaluation: the blinding key, the aggregation arithmetic on fixed ratings, number
normalisation in the speech-to-text metrics, the gate logic and --record, and the startup warning
reading the gates file. No network; no paid call."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from services.speech import evaluation
from services.speech.chain import startup_warning

CLIPS = [
    evaluation.Clip(
        "en", "lesson", 0, "Show 52 as 5 bundles.", "bodhan", "Kavya", "educational lecture"
    ),
    evaluation.Clip("en", "lesson", 0, "Show 52 as 5 bundles.", "sarvam", "ritu", None),
    evaluation.Clip("hi", "child", 1, "मुझे आ गया!", "bodhan", "Amit", "happy"),
    evaluation.Clip("hi", "child", 1, "मुझे आ गया!", "sarvam", "rahul", None),
]


# --- blinding ------------------------------------------------------------------------------------


def test_blinded_names_say_nothing_and_the_key_maps_every_clip_back() -> None:
    named, key = evaluation.blind(CLIPS, seed=7)
    names = [n for n, _ in named]
    assert len(set(names)) == len(CLIPS) and all(n.startswith("clip-") for n in names)
    for n in names:
        assert not any(
            w in n.lower() for w in ("bodhan", "sarvam", "kavya", "ritu", "amit", "rahul")
        )
    by = {k["clip"]: k for k in key}
    for n, c in named:
        assert (by[n]["provider"], by[n]["voice"], by[n]["language"]) == (
            c.provider,
            c.voice,
            c.language,
        )
    again, key2 = evaluation.blind(CLIPS, seed=7)
    assert again == named and key2 == key  # the same seed gives the same pack
    other, _ = evaluation.blind(CLIPS, seed=8)
    assert [n for n, _ in other] != names


# --- aggregation ----------------------------------------------------------------------------------


def write(path: Path, rows: list[dict[str, object]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rater", "clip", *evaluation.SCORES, "comment"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def fixture(tmp_path: Path) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    named, key = evaluation.blind(CLIPS, seed=7)
    name = {(c.provider, c.language): n for n, c in named}
    r1 = [
        {
            "rater": "A",
            "clip": name[("bodhan", "en")],
            "naturalness": 4,
            "clarity": 5,
            "numbers": 5,
            "suitability": 4,
        },
        {
            "rater": "A",
            "clip": name[("sarvam", "en")],
            "naturalness": 5,
            "clarity": 5,
            "numbers": 5,
            "suitability": 5,
        },
        {
            "rater": "A",
            "clip": name[("bodhan", "hi")],
            "naturalness": 3,
            "clarity": 4,
            "numbers": 2,
            "suitability": 3,
        },
        {
            "rater": "A",
            "clip": name[("sarvam", "hi")],
            "naturalness": 4,
            "clarity": 4,
            "numbers": 5,
            "suitability": 4,
        },
    ]
    r2 = [
        {
            "rater": "B",
            "clip": name[("bodhan", "en")],
            "naturalness": 5,
            "clarity": 4,
            "numbers": 4,
            "suitability": 5,
        },
        {
            "rater": "B",
            "clip": name[("sarvam", "en")],
            "naturalness": 4,
            "clarity": 4,
            "numbers": 5,
            "suitability": 4,
        },
        {
            "rater": "B",
            "clip": "clip-00000",
            "naturalness": 5,
            "clarity": 5,
            "numbers": 5,
            "suitability": 5,
        },
        {
            "rater": "B",
            "clip": name[("sarvam", "hi")],
            "naturalness": 9,
            "clarity": 4,
            "numbers": 5,
            "suitability": 4,
        },
    ]
    files = [write(tmp_path / "ratings-A.csv", r1), write(tmp_path / "ratings-B.csv", r2)]
    return evaluation.read_ratings(files), key


def test_the_means_and_the_numbers_wrong_share_are_computed_from_the_ratings(
    tmp_path: Path,
) -> None:
    ratings, key = fixture(tmp_path)
    agg = evaluation.aggregate(ratings, key)
    assert agg["rejected"] == 2  # an unknown clip and a score of 9
    b, s = agg["provider"]["bodhan"], agg["provider"]["sarvam"]
    assert b["ratings"] == 3 and s["ratings"] == 3
    assert b["naturalness"] == pytest.approx((4 + 3 + 5) / 3, abs=0.001)
    assert s["naturalness"] == pytest.approx((5 + 4 + 4) / 3, abs=0.001)
    assert b["numbers_wrong_share"] == pytest.approx(1 / 3, abs=0.0001)  # the Hindi clip scored 2
    assert s["numbers_wrong_share"] == 0.0
    assert agg["provider_language"]["bodhan / hi"]["ratings"] == 1
    assert agg["provider_voice"]["bodhan / Kavya"]["naturalness"] == 4.5


def test_the_tts_gate_against_its_thresholds(tmp_path: Path) -> None:
    ratings, key = fixture(tmp_path)
    gate = evaluation.tts_gate(evaluation.aggregate(ratings, key))
    assert gate["result"] == "fail"
    assert gate["checks"]["naturalness_gap"]["value"] == pytest.approx(0.333, abs=0.001)
    assert gate["checks"]["naturalness_gap"]["ok"] is False  # 4.33 against 4.0: more than 0.3 apart
    assert gate["checks"]["numbers_wrong_share"]["ok"] is False
    good = {
        "provider": {
            "bodhan": {"naturalness": 4.6, "numbers_wrong_share": 0.0},
            "sarvam": {"naturalness": 4.8, "numbers_wrong_share": 0.0},
        }
    }
    assert evaluation.tts_gate(good)["result"] == "pass"
    assert evaluation.tts_gate({"provider": {"sarvam": {}}})["result"] == "pending"


# --- speech to text -------------------------------------------------------------------------------


def test_numbers_said_as_words_or_digits_count_the_same() -> None:
    item = evaluation.stt_item(
        "Seventy-four minus 46: we borrow a ten.", "74 minus forty six we borrow a ten", "en"
    )
    assert (
        item["numbers"] == 3 and item["numbers_ok"] == 3 and item["cer"] == 0.0
    )  # 74, 46 and "a ten"
    assert item["terms"] == 2 and item["terms_ok"] == 2  # borrow, ten
    hi = evaluation.stt_item("चौहत्तर में से छियालीस, borrow करो", "74 में से 46 borrow करो", "hi")
    assert hi["numbers_ok"] == 2 and hi["terms_ok"] == 1
    missed = evaluation.stt_item("703 minus 468", "703 minus 486", "en")
    assert missed["numbers_ok"] == 1


def test_the_stt_summary_and_gate() -> None:
    rows = [
        {
            "provider": "bodhan",
            "language": "en",
            "tags": "redmi;quiet",
            **evaluation.stt_item("borrow a ten from 52", "borrow a ten from 52", "en"),
        },
        {
            "provider": "sarvam",
            "language": "en",
            "tags": "redmi;quiet",
            **evaluation.stt_item("borrow a ten from 52", "borrow a ten from 52", "en"),
        },
        {
            "provider": "bodhan",
            "language": "en",
            "tags": "galaxy;fan",
            **evaluation.stt_item("regroup the tens", "we group the tents", "en"),
        },
        {
            "provider": "sarvam",
            "language": "en",
            "tags": "galaxy;fan",
            **evaluation.stt_item("regroup the tens", "regroup the tens", "en"),
        },
    ]
    summary = evaluation.stt_summary(rows)
    assert summary["provider"]["sarvam"]["key_term_accuracy"] == 1.0
    assert summary["provider"]["bodhan"]["key_term_accuracy"] == pytest.approx(2 / 4)
    assert summary["provider_tag"]["bodhan / fan"]["items"] == 1
    gate = evaluation.stt_gate(summary)
    assert gate["result"] == "fail" and gate["checks"]["key_term_accuracy"]["ok"] is False
    assert evaluation.worst(rows, 1)[0]["provider"] == "bodhan"
    assert evaluation.stt_gate({"provider": {}})["result"] == "pending"


# --- the gates file -------------------------------------------------------------------------------


def test_record_writes_only_a_pass_or_fail_with_a_name_and_the_warning_reads_it(
    tmp_path: Path,
) -> None:
    gates = tmp_path / "speech_gates.md"
    gates.write_text(
        "---\nbodhan_tts: pending\nbodhan_stt: pending\ndate:\ndecided_by:\n---\n\n# Gates\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        evaluation.record("bodhan_tts", "pending", "Seema", path=gates)
    with pytest.raises(ValueError):
        evaluation.record("bodhan_tts", "pass", " ", path=gates)
    assert startup_warning(gates) is not None
    evaluation.record("bodhan_tts", "pass", "Seema", path=gates, details="- naturalness_gap: 0.1")
    state = evaluation.read_gates(gates)
    assert (
        state["bodhan_tts"] == "pass"
        and state["bodhan_stt"] == "pending"
        and state["decided_by"] == "Seema"
    )
    assert "for stt" in (startup_warning(gates) or "")
    evaluation.record("bodhan_stt", "pass", "Gopi", path=gates)
    assert startup_warning(gates) is None
    assert "# Gates" in gates.read_text(encoding="utf-8")  # the explanation is kept


def load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_aggregate_script_prints_the_gate_and_records_only_when_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ratings, key = fixture(tmp_path)
    (tmp_path / "key.json").write_text(json.dumps({"clips": key}), encoding="utf-8")
    gates = tmp_path / "gates.md"
    gates.write_text(
        "---\nbodhan_tts: pending\nbodhan_stt: pending\ndate:\ndecided_by:\n---\n", encoding="utf-8"
    )
    monkeypatch.setattr(evaluation, "GATES", gates)
    mod = load("speech_eval_aggregate")
    assert mod.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "text-to-speech gate: FAIL" in out and "numbers_wrong_share" in out
    assert evaluation.read_gates(gates)["bodhan_tts"] == "pending"  # not recorded without --record
    assert mod.main([str(tmp_path), "--record", "Seema"]) == 0
    assert evaluation.read_gates(gates)["bodhan_tts"] == "fail"
    assert (
        json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["gate"]["result"]
        == "fail"
    )


def test_the_stt_script_says_when_there_are_no_recordings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = load("speech_eval_stt")
    monkeypatch.setattr(mod, "DATA", tmp_path)
    assert mod.main([]) == 1
    assert "No recordings yet" in capsys.readouterr().out


def test_the_listening_pack_plan_counts_and_the_page_has_a_label_for_every_score() -> None:
    mod = load("speech_eval_pack")
    cs = mod.clips()
    p = mod.plan(cs)
    assert p["clips"] == 3 * 20 * 4 and p["bodhan"] == p["sarvam"] == 120 and p["cost_inr"] > 0
    page = mod.page([("clip-12345", b"OggS", "Show 52.")], {"clip-12345": "en"})
    assert page.count("<select") == 4 and page.count("aria-label=") >= 5
    assert (
        "data:audio/ogg;base64," in page
        and "http" not in page.split("<script>")[0].split("<body")[-1]
    )


# --- shadow mode ----------------------------------------------------------------------------------


def test_shadow_mode_logs_only_a_similarity_and_the_latency(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    from services.speech import audio, costs
    from services.speech.chain import ProviderChain
    from services.speech.service import SpeechService
    from tests.speech.test_practice_voice import Voiced

    first = Voiced("bodhan", heard="Meena show me 52 with bundles")
    second = Voiced("sarvam", heard="Meena show me 52 with the bundles")
    chain = ProviderChain(
        {"bodhan": first, "sarvam": second}, order=lambda f, lang: ["bodhan", "sarvam"]
    )
    svc = SpeechService("live", log=lambda **kw: None, providers=chain)
    wav = audio.tone(1.0, 300, rate=16000)
    assert svc._shadow([wav], "en", "x", "bodhan", 1.0, None) is None  # off by default
    monkeypatch.setenv("SPEECH_SHADOW_PROVIDER", "sarvam")
    monkeypatch.setenv("SPEECH_SHADOW_PER_MINUTE", "2")
    caplog.set_level(logging.INFO)
    budget = costs.SessionSpeechBudget(max_stt_seconds=100, max_tts_chars=100)
    text = svc.transcribe(wav, "en", budget=budget)
    th = svc._shadow([wav], "en", text, "bodhan", 1.0, budget)  # a second shadow call
    assert th is not None
    th.join(5)
    assert svc._shadow([wav], "en", text, "bodhan", 1.0, budget) is None  # rate-limited: 2 a minute
    import time

    time.sleep(0.2)
    logged = caplog.text
    assert "similarity=" in logged and "latency_ms=" in logged
    assert "Meena" not in logged and "bundles" not in logged  # never the texts
    assert budget.stt_seconds == pytest.approx(3.0, abs=0.1)  # main + two shadows, all counted
