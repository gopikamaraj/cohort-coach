# Numbers registry

Every number in the README, docs, reports and deck comes from one of these generated files. Regenerate with `python tasks.py evidence`.

| File | Source (script and input) | Date | Sample | Confidence note |
| --- | --- | --- | --- | --- |
| `docs/evidence/demo_verdicts.md` (+ `.json`) | `scripts/evidence.py` on `data/synthetic/block_T1T2.json` (hash `c43c94d0e056`) | n/a: seeded, simulated | 120 simulated classes, 2 terms | Simulated; small tracks carry their own note in the table |
| `docs/evidence/eval_summary.md` (eval 1) | `evals/runners/engine_items.py` | 2026-10-16 | 500 problems per error | Exact check, not a sample estimate |
| `docs/evidence/eval_summary.md` (eval 8) | `evals/runners/statistics.py` | 2026-10-16 | 100 planted and 100 no-effect simulated terms | Simulated terms; effect sizes and arm size are stated |
| `docs/evidence/eval_summary.md` (`evals/results/sim_fidelity.json`) | `evals/runners/sim_fidelity.py` | 2026-10-17 | 200 scripted simulator turns | Exact check |
| `docs/evidence/eval_summary.md` (`evals/results/sim_fidelity_live.json`) | `evals/runners/sim_fidelity.py --live` | 2026-10-17 | 60 live child-voice turns | Short live run: directional |
| `docs/evidence/eval_summary.md` (`evals/results/redteam.json`) | `evals/runners/redteam.py` | 2026-10-17 | 22 red-team seeds, code gates | Seed set: directional |
| `docs/evidence/eval_summary.md` (`evals/results/redteam_live.json`) | `evals/runners/redteam.py --live` | 2026-10-17 | 22 red-team seeds, with models | Seed set: directional |
| `docs/evidence/eval_summary.md` (`evals/results/practice_latency.json`) | `scripts/practice_latency.py --live` | 2026-10-17 | 21 live Practice Class turns | One network and machine: directional |
| `docs/evidence/eval_summary.md` (`evals/results/voice_latency.json`) | `scripts/voice_latency.py --live` | 2026-10-17 | 24 live Practice Class voice turns | One network and machine: directional |
| `docs/evidence/bundle_size.json` | `scripts/bundle_size.py --write` | 2026-10-17 | initial JS of the built PWA | Exact measurement |
| `docs/evidence/lighthouse_mobile.json` | `scripts/lighthouse_summary.py` | 2026-10-17 | one Lighthouse mobile run | One run: directional |
| `docs/evidence/practice_session_live.json` | `scripts/practice_cli.py --json` | 2026-10-17 | 7 turns of one scripted live session | One session: illustrative |
