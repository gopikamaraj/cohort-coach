# One app, one flow: what changed and what is left (31 Oct 2026)

## The flow now

A paper is made on Papers, generated from the rules or imported from a PDF or an answered sheet, and it carries its answer key. In Enter check the teacher chooses that paper; Start fetches the paper's own key to the phone (`GET /api/paper-hub/papers/{id}/key`, worked out by the engine from the paper's numbers in `services/papers/keys.py`). The answer boxes, the error finder, the stage counts, photo reading (call 8, `/api/sheets/read` with the paper id), `/api/stages` and before/after all use that key. Nobody is shown Form A or Form B, and the printed code no longer carries a form letter ("PRE · 3A · T1").

There is no pilot mode. `PILOT_MODE`, the pilot-only server, its sign-in and accounts, Upload sheets, Intervention audio and lesson links are removed (`services/pilot/`, `apps/pwa/src/pilot/`, `tests/pilot/`, and the `pilot_*` tables). The shared parts moved to `services/media/` (the lesson-audio store, the voice settings in `content/voices/lessons.v1.yaml`, and the local-store download route `/api/media/blob/...`). The landing page has no Mode menu and no mode chip. `run-all.bat` starts one back end and the web app.

The pilot runs in the same flow. The real pre-test is imported on Papers and chosen in Enter check. On the one machine that holds the pilot folder (`PILOT_DEMO=1`, `data/pilot/`), *Enter from the pilot sheets* reads the first sheet with call 8 using that paper's key, and fills the rest from the hand-keyed answer file.

The judge demo uses real papers too:
- Step 2 makes a paper from the rules.
- The demo class answers that paper, and the sheets and answer file are drawn from it.
- The post-test is that paper's twin.
- The judge's sample button and "use sample" start on the **sample paper**, a stored paper with the published pilot-test numbers that the sample sheets and photos were made on. It is chosen and keyed like any paper.
- "Load a simulated class" puts its checks on the sample paper and its twin.

Adaptive items: each key marks anchor items. The 5 adaptive items help find errors but are left out of before and after (`pairChecks`), as the design says. An imported paper has no adaptive items.

Evidence:
- `tests/papers/test_keys.py`: a paper with Form A's numbers gets Form A's key, and anchors are marked.
- `tests/papers_hub/test_api.py`: own key, imported key, no form question.
- `tests/pilot_demo/test_api.py`: read with the chosen paper.
- `apps/pwa/src/lib/paperKeys.test.ts`: the key is looked up by id; adaptive items are left out of before and after.
- `apps/pwa/e2e/paper-flow.spec.ts`, `checks.spec.ts`, `demo.spec.ts`, `pilot-demo.spec.ts`.

## What is still left

1. **Deployment.** The two Cloud Run services deployed on 26 Oct (pilot-only API and judge API) still run the old code. One service, `fln-cc-backend`, needs a redeploy and a database choice (SQLite or Cloud SQL). That choice is the owner's.
2. **The demo's AI read of sheet 1 in recorded mode.** The demo paper is now made from the rules, so its sheet pictures are new and have no recorded AI read. With a live key (the deployed demo) it is read live within the per-session cap. In CI and with `AI_MODE=recorded` the read cannot be replayed, so `demo.spec.ts` stands in for it and the reading summary is empty there. A recording needs one paid live run.
3. **The built-in forms A and B are still in the engine** (`engine/forms.py`, `generated/answer_keys.json`). They are the golden reference the engine tests check against, the numbers of the sample paper, the offline fallback for "Load a simulated class", and the list of pilot-test items no lesson may contain. Old checks saved on a phone before today still carry them and are labelled "Sample paper A/B".
4. **No lesson may contain a test item.** This is checked against the pilot test's items only (`ai/validators/check_items.py`), not against every paper a class has used. Extending it to all papers is not built.
5. **Pilot names that describe the pilot study, not a mode, are kept:** `PILOT_DEMO`, `services/pilot_demo/`, `/api/pilot-data/`, `tools/pilot/`, `python tasks.py pilot-ingest`, call 15, and the banner "Pilot data: real sheets, roll numbers only". `DemoEntry` is the component behind both the demo's step 4 and the pilot entry.
6. **Team documents still describe pilot mode:** `docs/submission/deck.md`, `docs/submission/slides.md`, `docs/build/PROGRESS.md`, `docs/design/stitch/INVENTORY.md`, generated `docs/evidence/browser_*`, and the QA scripts `scripts/browser_feature_table.py` and `scripts/browser_qa_report.py`. The history in `DECISIONS.md` and the old reports is kept as history.
7. **A paper's key needs a connection once.** It is fetched when the papers are listed in Enter check and when a check starts.
8. **Hindi and Tamil** for the new and changed lines are unreviewed drafts.
