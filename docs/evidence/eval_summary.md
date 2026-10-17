# Eval summary

Generated from `evals/results/*.json` by `scripts/evidence.py`. Run the evals with `python tasks.py eval all`. Simulated data is labelled where it is used.

## Eval 1: error answers and item collisions (`evals/results/engine_items.json`, 2026-10-16)

500 generated problems per error, compared with an independent column-procedure oracle (seed 2026). Bar: 100% correct, 0 collisions. Result: pass.

| Error | Item type | Problems | Matching oracle | Share | Collisions |
| --- | --- | --- | --- | --- | --- |
| ADD-NOCARRY | add_carry | 500 | 500 | 100% | 0 |
| PV-HEARD | dictation | 500 | 500 | 100% | 0 |
| PV-REVERSE | dictation | 500 | 500 | 100% | 0 |
| SUB-NODEC | sub_borrow | 500 | 500 | 100% | 0 |
| SUB-SFL | sub_borrow | 500 | 500 | 100% | 0 |

## Eval 8: statistics (`evals/results/statistics.json`, 2026-10-16)

Simulated terms (SIMULATED data): 20 classes per arm, 2000 bootstrap resamples, seed 2026, class-to-class effect spread 5.0 points. Planted working effects [15, 20, 25] points; no-effect trials planted 0.

- Recovery of planted working effects: 99% of 100 trials (bar at least 95%).
- False "working" with no effect: 0% of 100 trials (bar at most 5%).
- Result: pass.
- Scope of the recovery bar: it applies to planted effects of 15 points or more. Near the working bar, a planted 5-point effect was called working in 2 of 50 trials; a planted 10-point effect was called working in 27 of 50 trials (not scored).
- Eval 8 uses a simplified class-level simulator (binomial child counts, with natural drift and onset set to the same values as the simulated block). It tests the verdict code, not the answer-sheet model.

| Planted effect (points) | Trials | Working | Not working | Inconclusive | Scored |
| --- | --- | --- | --- | --- | --- |
| 0 | 100 | 0 | 100 | 0 | yes |
| 10 | 50 | 27 | 0 | 23 | no (information) |
| 15 | 34 | 33 | 0 | 1 | yes |
| 20 | 33 | 33 | 0 | 0 | yes |
| 25 | 33 | 33 | 0 | 0 | yes |
| 5 | 50 | 2 | 20 | 28 | no (information) |

## Eval 2: simulator fidelity (`evals/results/sim_fidelity.json`, 2026-10-17)

Scripted teacher turns drive the real simulator; every child number must be the engine's (the answer is the correct answer or one an independent oracle gives for the child's error, and every number in the line is in the plan's allowed set). Bar: 100%. Engine and template lines: 200 of 200 turns match (100%). Result: pass.

| Error | Turns | Matched |
| --- | --- | --- |
| ADD-NOCARRY | 50 | 50 |
| PV-HEARD | 50 | 50 |
| SUB-NODEC | 50 | 50 |
| SUB-SFL | 50 | 50 |

Live run with the real model (`evals/results/sim_fidelity_live.json`, 2026-10-17): 60 of 60 turns match (100%); the model's line was kept in 59 turns and replaced by the template in 1; cost USD 0.066561. This is a short live run (the full 200 turns are scheduled for P13).

## Red team (`evals/results/redteam.json`, `redteam_live.json`, 2026-10-17)

Seed set `evals/sets/redteam.yaml`: 22 attacks and 2 benign controls (seeds written by the build; the full 50 are still to be written). Code gates alone: 16 of 22 attacks blocked, 6 need a model.

Live run (call 7 and the call 2 labeller on the rest, 2026-10-17): 0 of 22 attacks reached a teacher (bar 0); 0 of 2 benign controls blocked. Result: pass. Small seed set: read as directional.

## Practice Class text-turn latency (`evals/results/practice_latency.json`, 2026-10-17)

21 scripted live turns over 3 sessions (label, engine, child line, gates): median 4968 ms, 90th percentile 5921 ms, maximum 10703 ms, against a target median under 3000 ms: does not meet the target. Cost USD 0.001587 per turn. From one network and one machine, so read as directional.
A/B with Haiku 5.5 for call 1 (`practice_latency_haiku_child.json`): median 8578 ms, 2 of 21 lines replaced by the template; not adopted.
