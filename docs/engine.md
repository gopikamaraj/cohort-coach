# The deterministic engine

Everything a judge must be able to trust is plain, unit-tested Python in `engine/`: the error functions, the items, diagnosis and the track choice. No AI call computes or states a number about a class. Claude may later phrase a sentence around a number; the number comes from here.

## The five errors

Each error is a pure function `problem -> set of wrong answers` in [engine/bugs.py](../engine/bugs.py).

| Code | Error | Example | Correct | Tracked |
| --- | --- | --- | --- | --- |
| PV-HEARD | Writes the number the way it is said | forty-three → 403; 346 → 30046, 3046, 300406 | 43; 346 | Yes, first priority |
| PV-REVERSE | Swaps tens and ones | 43 → 34; 346 → 364 | 43; 346 | Detected only |
| ADD-NOCARRY | Drops the carried ten | 47 + 25 → 62 | 72 | Yes |
| SUB-SFL | Smaller digit from larger in each column | 52 − 29 → 37 | 23 | Yes |
| SUB-NODEC | Borrows a ten, does not reduce the tens digit | 52 − 29 → 33 | 23 | Yes |

- An answer both heard and reversed (346 → 30064, 3064, 300604) counts for **both** PV-HEARD and PV-REVERSE.
- The untracked pattern `ADD-WHOLE-ONES` (38 + 47 → 715) is scored "other" but tallied separately: it may deserve a track.
- A number with a zero digit has no heard or reversed answer (the generator never makes one).
- Anything else a child writes is `other`; an empty box is `blank`; text the normaliser cannot turn into digits is `unreadable` and goes to a person. Blank and unreadable boxes never count towards an error.

## Items and forms

[engine/items.py](../engine/items.py) builds the 10-item check: 2 dictation, 3 addition with carrying, 1 anchor subtraction, 4 subtraction with borrowing.

| Type | Rules |
| --- | --- |
| Dictation | 3-digit; hundreds, tens, ones all non-zero; tens ≠ ones |
| Add-carry | 2-digit operands; ones total ≥ 10; sum ≤ 99 |
| Anchor | no borrowing; tens digit larger |
| Borrow | ones digit smaller; tens digit larger; ones-digit gap ≠ 5; result ≥ 10 |

`validate_item` also rejects any item where two errors give the same wrong answer, where an error answer equals the correct one, where the heard-and-reversed set overlaps a single error, or where the untracked answer collides with a tracked one. Example: 52 − 27 is rejected, since SUB-SFL and SUB-NODEC both give 35.

`generate_form(seed, like=...)` is deterministic. With `like`, it makes a **parallel form**: the same ones totals in items 3–5 and the same ones gaps in items 7–10, with every number different. The two printed pilot forms live in [engine/forms.py](../engine/forms.py); `tests/engine/test_forms.py` proves each item reproduces `pilot_forms.golden.json`.

## Diagnosis: the 2-item rule

[engine/diagnosis.py](../engine/diagnosis.py). A child **shows** an error only if it appears on at least 2 of the items that probe it: both of items 1–2, 2 of items 3–5, 2 of items 7–10. One slip is not a pattern. A wrong anchor (item 6) is noted, and items 7–10 are still scored.

For a class: prevalence p = children showing the error ÷ children checked (a fraction; the engine never rounds). **Eligible** = p ≥ 25% and at least 10 children checked, compared with integers (`count × 4 ≥ checked`), so 3 of 12 is eligible and 3 of 13 is not. **Track** = PV-HEARD if eligible, else the tracked error with the most children (ties go to the first in code order). PV-REVERSE is never chosen.

## One engine, two languages

The phone diagnoses offline with `apps/pwa/src/lib/diagnosis.ts`, which only looks up answers in `apps/pwa/src/generated/answer_keys.json` (written by `python tasks.py export-keys`, with a content hash so client and server can spot drift). Python also writes `tests/fixtures/diagnosis_cases.json` (named edge cases, seeded random children and whole classes of different sizes); pytest checks the files are not stale and Vitest checks TypeScript gives identical results.

## Why code, not AI

Diagnosis decides which teachers train together, so it must be exact, repeatable and explainable offline. A model can misread, drift between runs, and cannot show its working. Here every verdict traces to a table row and a rule above.

## Evidence

- `evals/results/engine_items.json` (eval 1, `python tasks.py eval engine_items`): 500 generated problems per error, compared with an independent column-procedure oracle: 100% correct, 0 collisions.
- Unit and property tests under `tests/engine/` (Hypothesis, 500 examples per property).

## Open for the team

- TODO-HUMAN(Seema): confirm the extra heard-and-reversed variants (3064, 300604 beside the printed 30064) and that all 20 pilot items match NCERT Grade 3.
