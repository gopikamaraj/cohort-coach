# P03 · AI platform and guardrails core — report

**Status:** ✅ · **Dates:** 2026-10-16 → 2026-10-16 · **Commits:** `a5c91c9`…`0eabec5` · **Gate:** none

## Summary

Every Claude call now goes through one path (`ai/client.py::run_call`) with versioned prompts, structured output, cache markers, bounded retries, deterministic fallbacks, a budget guard and one metadata-only audit row. Gates 1, 1b and 2 (validators, pre-filter, call 7), badges, explanation lines in en/hi/ta, a red-team harness with 12 seed attacks, judge endpoints and the README "Where AI is used" generator are built and tested offline. A live red-team run (12 checker calls, USD 0.0005) then confirmed the checker blocks both stereotype cases, passes both controls, and that prompt caching hits.

## What was built

| Area | Files | Notes |
| --- | --- | --- |
| Config, pricing, registry | `ai/config.py`, `ai/pricing.yaml`, `ai/pricing.py`, `ai/registry.py`, `ai/schemas.py` | 8 calls, five layers each; prices with source URL and date |
| Prompts | `ai/prompts/c01…c08 .v1.md`, `ai/prompt_loader.py` | v1 drafts; calls 1–3 refined in P04 |
| Call path | `ai/client.py`, `ai/audit.py` | modes recorded/live/record; refuses live with no key |
| Validators | `ai/validators/*` | numbers, quotes, length, language, pii, arithmetic, readability, prefilter; mypy strict |
| Guard | `ai/guard/{gates,badges,explain,rejections,flags}.py`, `ai/calls/c07_checker.py` | fails closed |
| Data | `services/api/db.py` | `ai_calls`, `review_items`, `review_decisions`, `teacher_flags`, `consents` |
| Word lists | `content/lang/`, `content/safety/`, `content/rejections/` | hi/ta lists are drafts (TODO-HUMAN) |
| Red team | `evals/sets/redteam.yaml`, `evals/runners/redteam.py` | 12 attacks + 2 controls |
| Ops | `scripts/budget.py`, `scripts/readme.py`, `services/api/judge.py`, `tasks.py` | `budget`, `readme`, `eval redteam` |
| Docs | `docs/guardrails.md`, `docs/architecture.md`, README section | |

## Acceptance

| Criterion | Proof | Key output | Status |
| --- | --- | --- | --- |
| Registry lists all 8 calls with five layers | `tests/ai/test_registry.py::test_registry_lists_all_eight_calls_with_all_five_layers`; `GET /api/judge/ai-map` test | passed | ✅ |
| Dummy recorded call passes every gate, complete audit row | `tests/ai/test_client.py::test_dummy_call_end_to_end`, `tests/ai/test_guard.py::test_child_line_passes_every_gate_and_is_badged_checked` | passed | ✅ |
| `pricing.yaml` has URL and date; DECISIONS holds the facts | `tests/ai/test_registry.py::test_pricing_has_source_url_and_date`; DECISIONS "P03 verified API facts" | passed | ✅ |
| `check` passes with the network disabled | `python tasks.py check` exit 0; `tests/conftest.py` autouse guard raises on any non-loopback connect, so a network call would fail a test | 333 passed | ✅ |

## Tests and evals

| Suite or eval | Count | Result | Bar | Source |
| --- | --- | --- | --- | --- |
| pytest (all) | 333 | passed | all pass | `python tasks.py check` output |
| pytest AI + red team | 96 | passed | all pass | `tests/ai`, `tests/evals/test_redteam.py` |
| Red team, live | 12 attacks, 2 controls | 10 blocked by code, 2 by the checker, 0 reached a teacher, 0 controls blocked | 0 unsafe reach a teacher | `evals/results/redteam.json` |

The bar is met on the 12 seed prompts only. It is not a claim about the full 50-prompt set (Shivani, P13), and the checker was run once per case.

## AI calls touched

| Call | Model | Prompt version | Validators | Eval | Live runs |
| --- | --- | --- | --- | --- | --- |
| 1–6, 8 | per `ai/config.py` | v1 | see registry | pending (P04, P13) | 0 runs, USD 0 |
| 7 | claude-haiku-5-5 | v1 | verdict consistency | red team, 12 seeds | 1 run, 4 calls logged, USD 0.0005 (`python tasks.py budget`) |

## Cost and latency measured

| Measure | Value | Source |
| --- | --- | --- |
| Checker spend | USD 0.0005 over 4 logged calls | `python tasks.py budget` (audit rows) |
| Cache | first call wrote 1353 tokens; 4059 tokens read from cache across the later calls | `python tasks.py budget`, `ai_calls` |

Latency is in each audit row; a median needs more calls (P04, P13).

## Deviations and decisions

| What changed | Why | DECISIONS |
| --- | --- | --- |
| Audit rows hold metadata only; `checker_reason` holds rubric codes, not free text | privacy review: free text could quote a teacher | "P03 design choices" |
| New `AI_BUDGET_USD_HARD` ceiling for judge traffic | judge traffic must still stop somewhere | "P03 design choices" |
| Recorded mode with no recording falls back instead of raising | shows the fallback path | "P03 design choices" |
| Validators were written before their tests in one batch (tests followed in the same task and drove four fixes) | speed | noted here only |

## Reviews

| Reviewer | Verdict | Blocking findings fixed | Open non-blocking |
| --- | --- | --- | --- |
| judge-reviewer | pass with fixes | this report; parking items | live checker evidence; cache-hit proof; AI-layers and audit links on the P05 judge landing |
| privacy-guardian | clear with fixes | `checker_reason` free text (`0eabec5`); `.hypothesis/` ignored | unsalted `input_hash`; scrub `record` fixtures (synthetic input only); keep `/api/judge/audit` off for real teachers in production (all in PARKING.md) |
| integrity-auditor | honest with fixes | none | red-team results not yet in `docs/evidence/`; say "12 seeds" not "12 cases"; Gopi to confirm the DECISIONS entries |

## Waiting on people

| Owner | Item | Placeholder in place | Needed by |
| --- | --- | --- | --- |
| Gopi | `ANTHROPIC_API_KEY` in `.env`, then `python tasks.py eval redteam --live` (a few cents) | recorded mode | P04 live checks |
| Gopi | Confirm the P03 DECISIONS entries (judge hard ceiling, audit design) | applied | P15 |
| Shivani, Gopi | Review hi/ta/Hinglish/Tanglish profanity lists; write the full 50 red-team prompts | 12 seeds, draft lists | P13 |
| Seema, Gopi | Native review of hi/ta number words, jargon, error names, badge and explanation wording | drafts | P09 |

## Judged areas served

AI use in layers: registry, README section, `/api/judge/ai-map`, `docs/architecture.md`. Guardrails: gates, badges, rejection loop, red team, `docs/guardrails.md`, `/api/judge/audit`.
