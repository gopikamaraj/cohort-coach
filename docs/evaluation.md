# Did the track work? Evaluation

Code answers this question, in [engine/evaluation.py](../engine/evaluation.py). Claude never computes or states a number about a class, a cohort or a track. Verdicts belong to a **track version** (for example "SUB-SFL v1"), pooled across its cohorts. A failed track counts against the track, never against a teacher.

## Two methods, one vocabulary

Every verdict is **working**, **not working** or **inconclusive**.

| | Block scale | Pilot scale |
| --- | --- | --- |
| When | Many classes on a track, with a waitlist comparison group | A handful of real classes, no comparison group |
| Effect | Change in p for track classes minus change in p for waitlist classes | The trained error's fall minus the mean fall of untrained errors that had p of at least 10% at pre-test |
| Uncertainty | 95% percentile bootstrap over classes (seeded) | Exact McNemar test on children who were Fixed versus New |
| Working | The whole interval is below 0 **and** the estimate is a fall of at least 10 points | Extra fall of at least 10 points **and** McNemar p below 0.05 |
| Not working | A fall of under 5 points, or a rise | Extra fall of under 5 points, or a rise |
| Inconclusive | Anything else, or fewer than 15 classes in either arm | Anything else, or no untrained error to compare with |
| Data | Class-level counts from the server | Child pairs by roll number, **on a phone or in a local script only** |

The comparison group at block scale is the waitlist: eligible teachers for the same track, grade and medium are randomly assigned this term or next, stratified by baseline p (terciles; each tercile is split as evenly as possible). If there is no waitlist, `engine/grouping.py` offers a matched group: same error, grade, medium and school type, baseline p within 5 points.

Pilot sheets carry roll numbers so that each child's two sheets can be paired. Pairing never runs on the server and raw pilot files never enter git; only the 2×2 counts leave the machine.

## The power caveat at pilot scale

A pilot has few classes and a few dozen children, and McNemar only counts children whose result changed. A real effect can easily come out **inconclusive**, and that is the honest answer. The block-scale evaluation (eval 8, [docs/evidence/eval_summary.md](evidence/eval_summary.md)) shows the same effect at scale: near the 10-point bar, planted effects are called "working" only part of the time. Treat pilot verdicts as evidence to read alongside teacher feedback, not as a pass mark.

## How small samples are worded

- Fewer than 15 classes in an arm: the verdict is **inconclusive**, with the reason `too_few_classes`.
- Fewer than 15 classes anywhere a figure is shown: a note reads "from N classes, read as directional" (`engine.evaluation.confidence_note`).
- Fewer than 5 classes: the figure is **hidden** in officer views and in the evidence tables ("hidden (fewer than 5 classes)").
- Teacher-facing text uses counts ("11 of 28 children"), never percentages.

## Evidence and how to reproduce it

| What | Command | File |
| --- | --- | --- |
| Demo verdicts (simulated block) | `python tasks.py evidence` | [docs/evidence/demo_verdicts.md](evidence/demo_verdicts.md) |
| Statistics eval (eval 8) | `python tasks.py eval statistics` | `evals/results/statistics.json`, summarised in [docs/evidence/eval_summary.md](evidence/eval_summary.md) |
| The simulated block (seed 2026) | `python tasks.py seed` | `data/synthetic/block_T1T2.json` |

Eval 8 plants effects of known size (and zero) in simulated terms and checks that planted working effects are called working at least 95% of the time and that no-effect terms are called working at most 5% of the time. Effect sizes, arm size, class-to-class spread and seeds are listed in its result file. The simulated block plants SUB-SFL v1 as a working track and SUB-NODEC v1 as a failing one; the verdicts are computed from the counts by `block_effect`, and a test swaps the planted effects to prove nothing is hardcoded.

All simulated data is labelled "simulated" wherever it is shown.
