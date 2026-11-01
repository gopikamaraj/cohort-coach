# Pilot sheets as a local demo data source: report

Prompt: `docs/build/Claude Code prompt pilot sheets as a local demo data source (folder, ingest scri.md`.
Decision: `docs/build/DECISIONS.md` (2026-11-01). How to use it: `docs/pilot/PILOT-DEMO.md`.

## What was built

| Part | Where |
| --- | --- |
| Folder rules, manifest, consent gate, `PILOT_DEMO` switch | `services/pilot_demo/config.py` |
| Answer file schema and builder (engine marks every answer; no new arithmetic) | `services/pilot_demo/answers.py` |
| Ingest: tidy, duplicates, class and roll, name scan, read, truth, diagnose, reports | `tools/pilot/ingest.py`, `python tasks.py pilot-ingest` |
| Call 15 (offline header read and name scan) | `ai/prompts/c15_pilot_sheet_scan.v2.md`, `ai/registry.py`, `ai/schemas.py`, `ai/config.py` |
| Routes: manifest, sheet, read, autofill (404 unless every condition holds; no-store) | `services/pilot_demo/api.py`, mounted before the demo router |
| Enter the check: Data source, class, first roll (gallery, list, file), Auto-fill, drawer, banner | `apps/pwa/src/components/DemoEntry.tsx`, `lib/demoStudio.ts`, `screens/DemoStudio.tsx` |
| Strings in en, hi, ta | `strings/*.json` (`pilot.*`) |

## Verification (command output)

- `pytest tests/pilot_demo`: 24 passed (ingest on a fake folder made from synthetic sheets, the answer file against the engine, the routes, the guards).
- Full Python suite: 2398 passed, 1 skipped, **2 failed**: `tests/chat/test_scheduler.py::test_a_question_with_no_answer_from_the_model_is_never_sent` and `::test_a_teacher_gets_at_most_three_ai_replies_a_day`. They fail on their own too. Nothing in `services/chat` or its tests was touched for this work. The code reads the real clock while the tests use fixed 29 Oct dates, which is the likely cause; **not confirmed**, so not fixed here.
- PWA: eslint clean, `tsc` clean, vitest 428 passed.
- Browser: `pilot-demo.spec.ts` 4 passed (with axe checks), plus demo, practice and landing specs: 37 passed in all. The pilot routes are stood in for with a fake class in the browser test; the real routes are covered by pytest.
- `ruff check .`, `ruff format --check .`, `mypy --strict engine ai/validators`: clean.

## Not done or not shown

- **No real sheet has been run.** `data/pilot/` does not exist on this machine, so the "look at a few normalised sheets" check was not possible; the tests use fake data. `docs/evidence/pilot_reading_accuracy.md` does not exist and will not until hand-keyed truth does.
- Call 15 has no live run and no eval bar (marked pending in the registry).
- A class dictated other numbers than 346 and 728 is built correctly in the answer file, but the on-phone error finder cannot diagnose it, so the screen disables that class with a reason (parked).
- Optional step 7 (the pilot classes' counts joining the simulated cohorts) was not built; later steps show the pilot banner and keep their own simulated labels.
- Pilot answers are held in the browser's memory only, so a reload loses them.
- The privacy, integrity and judge reviewer subagents were not run on this change.
