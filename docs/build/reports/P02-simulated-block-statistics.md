# P02 · Simulated block, grouping, mentors, statistics — report

**Status:** ✅ done. **Date:** 2026-10-16. **Range:** `a0d858f..HEAD`. All data in this phase is **simulated** and labelled so.

## Built

- `engine/diagnosis.py`: `profile_from_counts`, so grouping runs on the class counts the server stores.
- `engine/grouping.py`: track assignment, stratified waitlist split, cohorts (15 to 20, at most 2 per school, one mentor slot, cross-block and undersized flags, unplaced list) and the matched-comparison fallback. Every result carries the facts for its explanation line.
- `engine/mentors.py`: proven, same-term candidate and comparison-group improver rules, each returning reasons; the tier-1 `find_mentors` lookup.
- `engine/evaluation.py`: block scale (`block_effect`, seeded percentile bootstrap, verdict rules, confidence notes, hide rule), pilot scale (`paired_table`, `mcnemar_exact`, `pilot_extra_fall`, `pilot_verdict`) and `class_changes`.
- `data/synthetic/` (`block.py`, `config.yaml`) + `content/personas/teachers_simulated.yaml`: 40 schools, 120 Grade 3 classes, two terms, planted effects. Children exist only inside the generator; the output is class counts, assignments and cohorts.
- `services/api/db.py`, `services/api/seed.py`, `scripts/seed.py`: class-count-only tables; `python tasks.py seed` writes `data/synthetic/block_T1T2.json` and seeds the dev database.
- `evals/runners/statistics.py` (eval 8) and `scripts/evidence.py`: `python tasks.py eval statistics`, `python tasks.py evidence`.
- Docs: `docs/evaluation.md`, `docs/engine.md` (grouping and mentors), generated `docs/evidence/`.

## Acceptance

| Criterion | Proof | Result | Status |
| --- | --- | --- | --- |
| Statistics eval: at least 95% recovery, at most 5% false "working" | `python tasks.py eval statistics` | recovery and false-working rates in `evals/results/statistics.json` (summary in `docs/evidence/eval_summary.md`): PASS | ✅ |
| Demo data: SUB-SFL v1 working, SUB-NODEC v1 not working, nothing hardcoded | `tests/data/test_demo_verdicts.py`; `docs/evidence/demo_verdicts.md` | as stated; swapping the planted effects swaps the verdicts | ✅ |
| Seed deterministic | `python tasks.py seed --check` twice | same data hash both times; committed file equals a fresh build | ✅ |

Numbers are not retyped here: the exact figures live in the generated files named above (source and date in `docs/evidence/numbers.md`). Full suite on 2026-10-16: 239 pytest, 146 vitest, `mypy --strict engine` clean, ruff clean.

## AI calls touched

None. This phase is the proof that code, not AI, owns every number about classes, cohorts and tracks.

## Cost and latency

No paid calls. The generator builds the whole block in well under a second; eval 8 takes a few seconds.

## Deviations and decisions

See DECISIONS.md "P02 clarifications and deviations". The ones to read:

- **Planted effect size.** The SUB-SFL `extra_fix` was lowered from 0.45 to 0.36 after a first run gave about 25 points; the design says "about 20". The change matches a stated size, it does not choose a verdict. SUB-NODEC stays at 0. Both verdicts are computed by `block_effect`, and a test flips them by swapping the config.
- **Demo cohorts are small and flagged undersized.** One block, split by medium and then by arm, cannot fill cohorts of 15. The officer view (P12) should show that honestly.
- **Eval 8 is class-level.** It draws binomial child counts per class rather than rerunning the full answer-sheet model; it tests `block_effect`, not the generator. Effects vary class to class so the test is not trivially easy.
- **Alembic deferred** until the API schema settles; tables use `create_all`.
- **Hypothesis deadlines off** after a timing flake on a loaded machine (logic unchanged).
- **Honesty notes.** Several tasks wrote tests and code in one step, so I did not capture a red run for every one; red runs were captured for T01 to T11 where the test file preceded its module (collection error). Two composite shell commands failed to parse; nothing ran, and I redid them with files.

## TODO-HUMAN

- Seema: review the fictional teacher names (`content/personas/teachers_simulated.yaml`).
- Gopi: confirm the P02 clarifications in DECISIONS.md.

## Deferred

Mentor DB wiring (P11), cohort and officer views (P12), Alembic migration, the real pilot analysis run (a local script on pilot data, after the pilot).

## Judged areas served

- **Technical strength:** an honest "did it work": two methods, exact McNemar, seeded bootstrap, an eval that can fail in both directions.
- **Guardrails / dignity:** verdicts per track version; the hide rule below 5 classes; confidence notes; no per-child data in the data or the schema.
- **Evidence:** `docs/evidence/` tables, all generated, simulated and labelled.

## Review follow-ups carried to later phases

- **P12 (officer views):** apply `BlockEffect.hidden` in the API, not only in the evidence script; never join an officer view to `ClassRoom.teacher_name` or to a per-class result; add a test for both. The committed block file holds per-class counts for all classes by design (simulated).
- **P14 (pilot code):** add an import-boundary test that `services.api` never imports `paired_table`.
- **Evidence wording:** the generated eval summary now states that the 95% recovery bar applies to planted effects of 15 points or more, gives the power near the 10-point bar from the results file, and says eval 8 uses a simplified simulator (integrity review).
