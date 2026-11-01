# Report: Demo Studio (the judge's end-to-end demo flow)

Date: 2026-10-31. Source prompt: `docs/build/Claude Code prompt the end-to-end demo flow (Demo Studio).md`. Scope chosen by Gopi: everything in the prompt, keeping CLAUDE.md's one track per class per term.

## What was built

| Step | What | Where | Tests |
| --- | --- | --- | --- |
| A Scenario | `demo/scenarios/class_3a.yaml`: class 3A, 20 children, seed, planted errors, hard cases, the other classes and the post-test; children drawn with the simulated block's child model; truth kept apart from the answer file | `services/demo/scenario.py` | `tests/demo/test_scenario.py` |
| B Sheets | The printed pilot paper at 150 dpi, handwriting drawn into the layout map's boxes, carry and borrow marks, a smudge, a crossed-out answer, an empty box, a simulated phone photo, a "Demo sheet" footer and a PNG demo flag; named `3A-rollNN.png`; ZIP with `reads.json` and the blank paper. Images looked at and fixed (marks spilling into a box, the correction too small, the smudge blurring the border) | `services/demo/sheets.py`, `services/demo/fonts/` | `tests/demo/test_sheets.py` |
| C Reading and review | Sheet 1 read by call 8, cached by image hash, capped per session; Auto-fill from the answer file with no AI call, matched by file name or the sheet's demo label, code mismatch warning, non-demo photos read by the AI, upload of a lost answer file; a status per roll number; the bottom drawer; only approved sheets reach the error finder; demo reading summary | `services/demo/api.py`, `apps/pwa/src/components/DemoEntry.tsx` | `tests/demo/test_demo_api.py`, `apps/pwa/e2e/demo.spec.ts` |
| D Classes and cohorts | 24 simulated classes in 8 schools from the block generator; the real track assignment, waitlist split and cohort formation; same-term candidate mentors; three cohorts, hers this term and one next term | `services/demo/cohorts.py` | `tests/demo/test_scenario.py` |
| E Audio, Practice, chat | Lesson 1 drafted by call 5 with the class's numbers filled by code and voiced by the server voice, cached per scenario, "Demo: pre-approved"; Practice Class with the lesson's next step; a real cohort space and the chat service with a 60 second wait and Skip the wait | `services/demo/live.py`, `apps/pwa/src/screens/DemoStudio.tsx` | `tests/demo/test_demo_api.py`, `apps/pwa/e2e/demo.spec.ts` |
| F Coach and officer | The coach's queue: her question (answered in the coach's own words when the AI has no source), a simulated mentor's method card through the real mentor-item states, the AI draft of lesson 2 in the real review queue; the officer's dashboard with cells under 5 classes hidden and before and after by cohort | `services/demo/live.py`, `services/demo/cohorts.py` | same |
| G Stepper and reset | Demo step n of 11 on every screen, Back, Next (right screen, right role), the judge guide's question, Reset (this device's demo only); optional step 12 | `apps/pwa/src/components/DemoPanel.tsx`, `apps/pwa/src/lib/demoStudio.ts` | `apps/pwa/e2e/demo.spec.ts` |
| H Tests | 25 Python tests; 4 browser tests (all 12 steps with axe on each new screen, the drawer on a laptop, Hindi, two devices) replaying recorded AI answers | `tests/demo/`, `apps/pwa/e2e/demo.spec.ts`, `ai/fixtures/recorded/` | |
| I Evidence and docs | Reading summary on synthetic sheets and one run's cost and time; README steps; rubric rows E2.6 and A2.8; AI_USAGE; judge help; inventory X36 and X37 | `scripts/demo_evidence.py`, `docs/evidence/demo_synthetic_reading.md` | |

## Differences from the prompt

See `docs/build/DECISIONS.md` (2026-10-31). In short: one track a term; tracked errors only; the pilot paper; the sheet's demo label instead of reading the roll box; the chat AI says it has no source until the strategies are approved.

## Human checks

- Seema: approve (or change) the teaching strategies, so the demo chat can answer from them; replace the simulated mentor card with a real one when an interview exists.
- Shivani (Hindi) and Gopi (Tamil): the demo screen wording.
- Someone: time a person running the demo once.
