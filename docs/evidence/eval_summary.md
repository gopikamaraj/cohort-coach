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

| Planted effect (points) | Trials | Working | Not working | Inconclusive | Scored |
| --- | --- | --- | --- | --- | --- |
| 0 | 100 | 0 | 100 | 0 | yes |
| 10 | 50 | 27 | 0 | 23 | no (information) |
| 15 | 34 | 33 | 0 | 1 | yes |
| 20 | 33 | 33 | 0 | 0 | yes |
| 25 | 33 | 33 | 0 | 0 | yes |
| 5 | 50 | 2 | 20 | 28 | no (information) |
