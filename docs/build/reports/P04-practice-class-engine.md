# P04 · Practice Class engine and calls 1–3 (text) — report

**Status:** 🟡 done; one acceptance criterion (text-turn latency under 3 s) not met, with a stated plan · **Dates:** 2026-10-17 → 2026-10-17 · **Commits:** `3a82c5d`…(this report) · **Gate 1:** passed for the end-to-end rehearsal, recorded and live; latency target missed

## Summary

A full SUB-SFL rehearsal now runs end to end in text: teacher line → labeller (call 2) → seeded engine → child voice (call 1) → gates (validators, pre-filter, call 7) → reply, and the feedback card (call 3) at the end, with two verbatim quotes. It runs through the terminal, the library and the API, in recorded mode (replaying a real session recorded the same day), once live, and offline through a rule-based stub. Every number a child says is made by code. All four tracked errors have scenarios, move lists and rubrics (SUB-SFL and SUB-NODEC are Seema's priority; PV-HEARD and ADD-NOCARRY are drafts). Not met: the median text turn is about 5 s against the 3 s target, because three network calls run in series.

## What was built

| Area | Files | Notes |
| --- | --- | --- |
| Simulator | `engine/simulator.py` | Pure, seeded per turn; moves, strength and engagement, shy child, quiet after scolding, end conditions, seat filling, steps as data |
| Content | `content/{movelists,rubrics,scenarios,personas,templates,schemas}/`, `services/practice/content.py` | 4 errors × (move list, rubric, scenario); 12 fictional children in 3 languages; child-line templates in 3 languages; JSON Schemas exported |
| Calls | `ai/calls/c01_child_voice.py`, `c02_move_label.py`, `c03_feedback.py`; prompts c01 v2, c02 v3, c03 v2, c07 v4 | Guards listed in `docs/practice-class.md` |
| Session and API | `services/practice/session.py`, `services/api/practice.py` | Memory only, 2-hour limit, `layers` trace on every turn, 40-turn cap |
| Offline | `services/practice/stub_client.py`, `scripts/practice_cli.py` | `AI_MODE=stub`, `python tasks.py practice` |
| Evals | `evals/runners/sim_fidelity.py`, `evals/sets/sim_fidelity/`, `evals/sets/redteam.yaml` (+10 injection lines), `scripts/practice_latency.py` | Results in `evals/results/`, summary in `docs/evidence/eval_summary.md` |
| Docs | `docs/practice-class.md`, DECISIONS (3 entries) | Includes one live turn's five layers |

## Acceptance

| Criterion | Proof | Key output | Status |
| --- | --- | --- | --- |
| Full SUB-SFL session in English via the CLI and the API in recorded mode, and once live (cost and latency logged), ending in a card with two verbatim quotes | `tests/practice/test_recorded_session.py` (library, API, CLI); live: `docs/evidence/practice_session_live.json` | 7 turns, card badge checked, 2 strengths whose quotes are verbatim in her turns; live cost and per-turn latency in the file | ✅ |
| Live fidelity run of ≥ 50 turns shows 100% numeric match | `evals/results/sim_fidelity_live.json` | 60 of 60 turns match (15 per error); 59 lines from the model, 1 template | ✅ |
| Injection seeds: child stays in role, labeller tags off_task, nothing unsafe passes the gates | `evals/results/redteam_live.json`, `tests/practice/test_session.py::test_injection_lines_are_off_task_and_the_child_stays_in_role` | 0 of 22 attacks reached a teacher, 0 of 2 controls blocked (seed set; directional) | ✅ |
| Median text-turn latency measured against < 3 s; if over, the report states the plan | `evals/results/practice_latency.json` | median 4968 ms, p90 5921 ms over 21 live turns: **over target** | ❌ plan stated |

**Latency plan** (also in DECISIONS and `docs/practice-class.md`). Three serial calls of about 1.5 to 2 s each (labeller, child line, checker) set the floor. Already tried: thinking off for the short calls, shorter checker reasons, smaller token use, an A/B with Haiku 5.5 for call 1 (slower, `practice_latency_haiku_child.json`). Next: in voice mode the checker runs while the speech is synthesised, hiding its time (P07); the API server near the Claude endpoint (P15); then re-measure. No bar was changed.

## Tests and evals

| Suite or eval | Count | Result | Bar | Source |
| --- | --- | --- | --- | --- |
| pytest (all) | 485 | passed | all pass | `python tasks.py check` |
| Simulator fidelity, engine and templates | 200 scripted turns | 200 match | 100% | `evals/results/sim_fidelity.json` |
| Simulator fidelity, live model | 60 turns | 60 match | 100% | `evals/results/sim_fidelity_live.json` |
| Red team, live | 22 attacks, 2 controls | 0 reached a teacher, 0 controls blocked | 0 unsafe | `evals/results/redteam_live.json` |
| Text-turn latency, live | 21 turns | median 4968 ms | < 3000 ms | `evals/results/practice_latency.json` |

Human-rated realism (call 1) and usefulness (call 3) show **pending**: no ratings exist yet.

## AI calls touched

| Call | Model | Prompt | Validators | Eval | Live runs |
| --- | --- | --- | --- | --- | --- |
| 1 child voice | claude-sonnet-5-5 | v2 | numbers ⊆ plan, no number words, length, language, pre-filter, answer present | fidelity 60/60 live; realism pending | in the runs above |
| 2 labeller | claude-haiku-5-5 | v3 | enum label set, confidence bar, injection override, posed-problem checks | agreement on 150 lines pending (Shivani, P13) | in the runs above |
| 3 feedback | claude-sonnet-5-5 | v2 | verbatim quotes in her turn, rubric points and evidence, no scores, numbers | usefulness pending | one live session |
| 7 checker | claude-haiku-5-5 | v4 | verdict consistency | red team 22 live | in the runs above |

## Cost and latency measured

Cost per text turn about USD 0.0016 (`practice_latency.json`); one scripted live session with feedback USD 0.0288 (`practice_session_live.json`). Prompt caching confirmed: later calls read the cached system block (see `cache_read` in the session file). Total live spend for P04 stays well under USD 1 (`python tasks.py budget`).

## Deviations and decisions

| What changed | Why | DECISIONS |
| --- | --- | --- |
| Checker no longer judges maths or fit on simulated child lines | live run: it read deliberate wrong answers as errors; code checks every number | "P04 AI settings found by live runs"; `docs/guardrails.md` states it |
| Thinking off for calls 1, 2, 6, 7 (per-model spelling) | checker ran out of tokens on thinking; latency | same |
| Child readability limit 12 → 20 words per sentence | a child's step-by-step working is one sentence; 30-word cap unchanged | "P04 Practice Class decisions" |
| Tamil number-word list drops ஒன்று, பத்து, நூறு | they are the Tamil place-value words | same |
| Red-team seed set 12 → 22 | the brief asked for 10 injection lines; bar unchanged | same |
| Tests were written with the code for the simulator and validators, not strictly first for every file | speed; every file has tests and the sabotage tests prove the evals can fail | noted here |

## Reviews

| Reviewer | Verdict | Blocking findings fixed | Open non-blocking |
| --- | --- | --- | --- |
| judge-reviewer | pass with fixes | committed live session with layers sample (`docs/evidence/practice_session_live.json`, excerpt in `docs/practice-class.md`); PARKING items | text-turn fix pending P07/P15; AI-layers overlay screenshot (P06) |
| privacy-guardian | clear with fixes | `--record` now needs `--script` and warns | `judge` flag is client-set; no rate limit on `/api/practice`; personas await Seema's review (all in PARKING) |
| integrity-auditor | honest with fixes | `docs/guardrails.md` now states the checker exception | DECISIONS entries need Gopi's confirmation |

## Waiting on people

| Owner | Item | Placeholder in place | Needed by |
| --- | --- | --- | --- |
| Seema | Review move lists, rubrics, scenario values (incl. placeholders `exchange_ten`, `regroup_ten`, `show_chart` −0.3), personas | yes | P06 staging |
| Seema, Gopi | Native review of Hindi and Tamil child-line templates, move and rubric wording, error names | yes (drafts) | P06 |
| Shivani | 150 human-labelled lines for the labeller eval; teacher realism ratings; 50 red-team prompts | no ratings yet | P13 |
| Gopi | Confirm the P04 DECISIONS entries | applied | P15 |

## Judged areas served

AI use in layers (the hero): the `layers` trace, `docs/practice-class.md` with a live turn in five layers, the registry. Guardrails: validators, template fallback, gates, injection handling, live red team. Real scenarios: template and stub fallbacks keep a rehearsal running when a call fails or times out.
