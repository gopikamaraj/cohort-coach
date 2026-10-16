# Numbers registry

Every number in the README, docs, reports and deck comes from one of these generated files. Regenerate with `python tasks.py evidence`.

| File | Source (script and input) | Date | Sample | Confidence note |
| --- | --- | --- | --- | --- |
| `docs/evidence/demo_verdicts.md` (+ `.json`) | `scripts/evidence.py` on `data/synthetic/block_T1T2.json` (hash `c43c94d0e056`) | n/a: seeded, simulated | 120 simulated classes, 2 terms | Simulated; small tracks carry their own note in the table |
| `docs/evidence/eval_summary.md` (eval 1) | `evals/runners/engine_items.py` | 2026-10-16 | 500 problems per error | Exact check, not a sample estimate |
| `docs/evidence/eval_summary.md` (eval 8) | `evals/runners/statistics.py` | 2026-10-16 | 100 planted and 100 no-effect simulated terms | Simulated terms; effect sizes and arm size are stated |
