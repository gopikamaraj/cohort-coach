# The deterministic engine

**Code, not AI, owns every number.** Eval 1 (`evals/results/engine_items.json`) checks the error answers and item collisions; the phone and the server give identical diagnoses (see "One engine, two languages").

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

## Grouping and mentors

[engine/grouping.py](../engine/grouping.py) works on **class-level counts only** (what the server stores), through `profile_from_counts`.

1. **Track assignment.** A class is eligible at p of at least 25% with at least 10 children checked. One track per class: PV-HEARD first, otherwise its highest-p error. Each assignment returns the facts for its one-line explanation ("Grouped for SUB-SFL because 11 of 28 children showed it").
2. **Waitlist split.** Teachers with the same track, grade and medium are cut into terciles of baseline p and each tercile is split as evenly as possible (never more than one apart), with a seeded shuffle. The same seed always gives the same split.
3. **Cohorts.** 15 to 20 teachers, at most 2 per school, one mentor slot each. A block with fewer than 15 eligible teachers is pooled with other short blocks (flagged `cross_block`); a pool still under 15 becomes one `undersized` cohort. Teachers who do not fit (school cap or a full cohort) are returned as `unplaced` for the next cohort. The demo block is one block split by medium and then by arm, so its cohorts are small and flagged undersized.

[engine/mentors.py](../engine/mentors.py) returns, for each rule, whether it was met and the numbers behind it. Exact fractions decide every boundary.

| Kind | Rule |
| --- | --- |
| Proven | On the track; last term p of at least 25%; this term fell at least 15 points and by at least half; at least 15 children checked both times; her fall beats the comparison group's average; she consents |
| Comparison-group improver | The proven bar, without the track and without the comparison-average rule; she consents |
| Same-term candidate | Same grade and medium; p of at most 5% while the block average is at least 25%; at least 10 children checked; she consents. The cause is unverified, so a method interview comes first and she stays "candidate" until a term confirms |

`find_mentors` is the tier-1 exact lookup (error, grade, medium, status, verified) that P11 wires to the database. There is no vector database.

## One engine, two languages

The phone diagnoses offline with `apps/pwa/src/lib/diagnosis.ts`, which only looks up answers in `apps/pwa/src/generated/answer_keys.json` (written by `python tasks.py export-keys`, with a content hash so client and server can spot drift). Python also writes `tests/fixtures/diagnosis_cases.json` (parity fixtures: their expected values are the engine's own output, so they prove Python and TypeScript agree, not that either is right; correctness rests on the printed key and the hand-written assertions in `tests/engine/`) (named edge cases, seeded random children and whole classes of different sizes); pytest checks the files are not stale and Vitest checks TypeScript gives identical results.

## Why code, not AI

Diagnosis decides which teachers train together, so it must be exact, repeatable and explainable offline. A model can misread, drift between runs, and cannot show its working. Here every verdict traces to a table row and a rule above.

## Running the checks

Use `python tasks.py test` (or `check`), which use the project venv. Bare `pytest` on system Python lacks Hypothesis.

## Evidence

No number is typed in this page. The results live in generated files:

- `evals/results/engine_items.json` (eval 1, `python tasks.py eval engine_items`): per error, how many generated problems match an independent column-procedure oracle, and how many collide. The registry copy in `docs/evidence/` arrives with `python tasks.py evidence` (P02).
- Unit and property tests under `tests/engine/` (Hypothesis, 500 examples per property): run `python tasks.py test`.
- Type check: `.venv/Scripts/python.exe -m mypy --strict engine` (the venv has mypy; system Python may not).

## Open for the team

- TODO-HUMAN(Seema): confirm the extra heard-and-reversed variants (3064, 300604 beside the printed 30064) and that all 20 pilot items match NCERT Grade 3.
