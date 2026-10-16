# Demo verdicts (SIMULATED)

> SIMULATED DATA: a fictional block built for demonstration. No real school, teacher or child.

Source: `data/synthetic/block_T1T2.json` (data hash `c43c94d0e0567ed9f0e318ac9f8352007a88aa5bb7e280869ec111aafa57725f`, seed 2026), evaluated by `engine.evaluation.block_effect` (95% percentile bootstrap over classes, 2000 resamples, seed 2026) through `scripts/evidence.py`. Effect = change in prevalence of the track's error for track classes minus the same for waitlist (comparison) classes, in percentage points; negative means the track classes fell more. Verdicts are per track version, never per teacher. A figure covering fewer than 5 classes is hidden.

| Track version | Classes (track / comparison) | Effect (points) | 95% CI | Verdict | Note |
| --- | --- | --- | --- | --- | --- |
| PV-HEARD v1 | hidden (fewer than 5 classes) | hidden (fewer than 5 classes) | hidden (fewer than 5 classes) | inconclusive | from 3 classes, read as directional |
| ADD-NOCARRY v1 | 8 / 7 | -15.7 | -23.0 to -8.8 | inconclusive | from 7 classes, read as directional |
| SUB-SFL v1 | 21 / 23 | -19.5 | -24.1 to -15.1 | working |  |
| SUB-NODEC v1 | 18 / 17 | -0.3 | -3.3 to 2.8 | not_working |  |
