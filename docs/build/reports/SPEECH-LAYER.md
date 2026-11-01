# Speech layer: Bodhan AI first, Sarvam as the fallback (Prompt 1)

Built on 1 Nov 2026 on branch `speech-bodhan`, from Prompt 1 of `docs/build/bodhan-speech-prompts.md`. Not merged: today is the evaluation freeze. Nothing is committed. Live calls: none. Every test uses a mock, and the test suite blocks all network sockets.

## What changed

All live speech now goes through one provider interface. **Bodhan AI is the first provider and Sarvam the fallback**, for both speech to text and text to speech. A provider with no key is skipped. A failing provider is skipped for 30 seconds after 3 failures in 60 seconds.

| File | What |
| --- | --- |
| `services/speech/provider.py` (new) | `SpeechProvider` interface (`transcribe`, `synthesize`, `capabilities`, `configured_for`), the `Transcript` and `Audio` results, `SarvamProvider` (wraps the existing client, requests unchanged), `MockProvider` |
| `services/speech/bodhan.py` (new) | `BodhanClient` and `BodhanProvider`: httpx with explicit timeouts (connect 5 s, speech to text 20 s, text to speech 30 s, all set by `.env`), the status mapping below, one retry with backoff and jitter honouring `Retry-After`, rate-limit headers read when present, the 45 voices and 14 styles from the API page |
| `services/speech/chain.py` (new) | `ProviderChain`: order from `SPEECH_TTS_PROVIDERS` and `SPEECH_STT_PROVIDERS` (default `bodhan,sarvam`, with per-language overrides), fallback rules, a breaker per provider and function, fallback counts, the startup warning |
| `services/speech/costs.py` (new), `content/speech_prices.yaml` (new) | Cost per call from the price file (every paid price `verified: false`), and `SessionSpeechBudget` (per-session caps on speech-to-text seconds and text-to-speech characters) |
| `services/speech/audio.py` | Added `to_wav_16k_mono` (rewrites the header with the true length), `duration_seconds` (survives a streamed WAV with no size), `trim_silence`, `split_for_stt` (pieces of at most 28 s, cut at real silence or at the limit), `wav_to_mp3` (48 kbps mono), `loudness_normalise` (about −16 LUFS), `concat` |
| `services/speech/health.py` | The breaker takes an optional window ("3 failures in 60 s"). Without it, it behaves as before |
| `services/speech/service.py` | `SpeechService` takes a chain. Speech to text: convert → refuse over 30 s (as before) → trim silence → split at 28 s → chain → join. Text to speech: chain → OGG/Opus, pitch-shifted per child, cached. Both accept a session budget. `default_service()` builds the chain in live mode. A `SpeechService` given a Sarvam client keeps the old path |
| `services/api/main.py` | Logs the startup warning (never blocks) when `SPEECH_MODE` is not `stub` |
| `scripts/check_bodhan.py` (new) | Key check and round trip: synthesizes one Hindi sentence, transcribes it back. `--no-live` checks configuration only |
| `tests/speech/bodhan_mock.py`, `test_bodhan.py`, `test_chain.py`, `test_audio_layer.py`, `test_check_bodhan.py` (new) | 64 tests |
| `tests/conftest.py` | One more automatic fixture: the switches added on 1 Nov (Bodhan keys, provider order, `SIMULATOR_MODEL`, `BAYES_*`, `DEV_TESTING`) are removed for the suite, so tests do not depend on a developer's `.env` |
| `docs/vendors/bodhan/api-reference.md` (new) | Dated notes from the API page (read 1 Nov 2026) |
| `.env.example`, `README.md`, `AI_USAGE.md`, `docs/build/DECISIONS.md` | Keys, order, timeouts, caps; external services, ffmpeg and attribution; the speech row; the decision |

`ffmpeg` was already installed in the `Dockerfile` (line 7) and is on PATH in this dev machine (WinGet).

## Bodhan status mapping

| Status | Kind | Retried | Falls back to Sarvam | Logged |
| --- | --- | --- | --- | --- |
| 200 | ok | n/a | n/a | model, status, latency, request id |
| 401, 403 | `auth` | no | **yes** (a key problem at Bodhan, not our request) | as 200 |
| 415 | `bad_request` | no | no (our conversion is wrong; it would fail everywhere) | **error level**, "our conversion to WAV is wrong" |
| 422 | `bad_request` | no | no | warning with the unknown value named in the reply (a voice, language or style, never the text) |
| 400, other 4xx | `bad_request` | no | no | as 200 |
| 429 | `rate` | once, after `Retry-After` (at most 10 s) or 0.5 to 1 s | yes | as 200 |
| 5xx | `unavailable` | once | yes | as 200 |
| timeout, network | `timeout`, `unavailable` | once | yes | as 200 |
| open circuit | `unavailable` (`breaker_open`) | n/a | yes | a fallback line |

Never logged: a key, the audio, the text sent, the transcript. Tested in `test_the_logs_hold_no_key_no_text_and_no_audio`.

## Tests

| | Before | After |
| --- | --- | --- |
| `tests/speech/` | 26 passed | 90 passed (26 old, unchanged, plus 64 new) |
| The speech-related files across the suite (`tests/speech`, `tests/content/test_review_api.py`, `test_model_run.py`, `test_publish.py`, `tests/api/test_health.py`, `tests/practice/test_api.py`, `tests/cohort_run/test_api.py`) | 63 passed in the first four of these before the change | 171 passed |

Also checked: `ruff check` and `ruff format` clean on every touched file, `mypy services/speech` clean, and `tests/test_ai_usage_doc.py` (path and status checks) passes once this report exists.

**The "Done when" items.**
- Tests pass with no live call: yes (above).
- A mock run shows Bodhan first and Sarvam as the fallback: `test_the_service_uses_bodhan_first_and_sarvam_when_bodhan_is_down`. Bodhan answers when it is up, and Sarvam is not called. With Bodhan returning 503 twice, Sarvam answers and one fallback is counted.
- `check_bodhan.py --no-live` works: exit 0, with keys shown as their first 4 characters and length.
- You can run `check_bodhan.py` live with your keys: the script is ready and tested against the mock, including exit 2 for a speak-key failure and exit 3 for a transcribe-key failure. **I didn't run it live.** Per the runner rules, live calls happen only when you run them.

## Unclear or missing in Bodhan's docs

- **Error statuses:** only 415 (speech to text) and 422 (text to speech) are documented. We map 401, 403, 429 and 5xx as for any HTTP API.
- **Over-length audio:** the page says audio over 30 s is rejected but gives no status. We never send more than 28 s.
- **Rate-limit headers and error envelope:** documented for translation and transliteration only. We read the headers if present and don't depend on the envelope.
- **Prices:** none on the API page. The figures in `content/speech_prices.yaml` come from an unverified article. Check https://console.bodhan.ai/#pricing (Prompt 4 asks you to confirm them).
- **Terms and attribution:** none on the API page. The attribution line "Bodhan AI / AI4Bharat (Indic-Speak, Indic-Transcribe)" is in the README as the prompt asks. The terms check is Prompt 4.
- **`language`** is optional for speech to text (auto-detected). We always send it.

## Found and fixed on the way

ffmpeg writing to a pipe leaves the WAV size fields unset. The mock, which measures the header like a metering service would, refused such a file as longer than 30 s. `to_wav_16k_mono` now rewrites the header with the true length (`test_the_converted_wav_header_carries_the_true_length`). The chain path already rewrote each piece, so only a direct send, as in the check script, was affected.

## Not done in Prompt 1 (later prompts)

- **Prompt 2:** the Bodhan voice cast (one default voice per language for now, `TODO-HUMAN(Seema)`), lesson splitting and stitching, the round-trip check.
- **Prompt 3:** wiring the per-session caps to Practice Class sessions and the "voice is off" message, the browser recorder's 25-second timer, mood-to-style.
- **Prompt 4:** the gates file and evaluation. Until `docs/evidence/speech_gates.md` records both gates as passed, the startup warning is logged whenever Bodhan is first.
