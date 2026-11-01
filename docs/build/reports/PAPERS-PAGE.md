# Papers page: report

Prompt: `docs/build/Claude Code prompt the Papers page (create and manage test papers, import from P.md`.
Decisions: `docs/build/DECISIONS.md` (2026-11-01, two entries). Status rows: `docs/RUBRIC_MAP.md` A2.10 and A2.11.

## What is built

| Step | What | Where |
| --- | --- | --- |
| 1 | Papers sits between Home and Enter check (teacher, mentor, judge; coach keeps its bar; none for officers) | `apps/pwa/src/App.tsx` |
| 1b | Scopes on the server: teacher own class; mentor inside cohorts she mentors; coach inside cohorts assigned and, before cohorts exist, any known class; officer none | `services/papers_hub/service.py`, `api.py` |
| 2 | The list: form, kind, status, source, imported or awaiting review, cohort badge and reason, filters; server-side scoped list for coach and mentor; archive | `Papers.tsx`, `papers_hub/api.py` |
| 3 | Create a paper: Generate from rules (Paper Studio, same test ids) and From a PDF | `Papers.tsx` (`CreatePaper`) |
| 3b | Assign: panel, cohort option only for post-test and termly, one row per class, duplicate refused, no withdrawal after a sheet, notes without personal data, Assigned to you, counts-only progress | `service.py`, `PaperHubParts.tsx` |
| 4 | PDF import: call 16 reads the printed questions; code computes keys, probes, wrong answers, coverage; independent check; printed-key mismatch flagged; handwriting drops printed answers; merge of up to three photos; 24-hour deletion; confirm to a paper | `ai/prompts/c16_paper_read.v1.md`, `importer.py`, `service.py`, `PaperImport.tsx` |
| 5 | Cohort status with the reason and next action | `lib/paperStatus.ts` (phone), `paper_status` (server) |
| 6 | Detail tabs (read only) | `PaperHubParts.tsx` |
| 7 | Enter check chooses a paper; creation is gone from it; the demo's step 2 is on the Papers page | `StartCheck.tsx`, `PaperChooser` |
| 8, 8b | `paper_status` read-only assistant tool; open questions made by code and asked one at a time; whitelisted edits tagged "Assistant changed this" with Undo; Confirm and Assign stay human; `papers` screen id; help documents and suggested questions in the teacher, mentor, coach and judge banks | `assistant/tools.py`, `importer.open_questions`, `docs/help/*.md`, `docs/assistant_questions/*.json` |
| 10 | DECISIONS, AI_USAGE (call 16), RUBRIC_MAP, INVENTORY, Stitch prompts X38 and X39, README, this report | |

## Verification (command output)

- `pytest tests/papers_hub`: 41 passed (importer 11, API and scopes 29, recorded reader 1).
- Full Python suite before the last two fixes: 2451 passed, 1 skipped, 3 failed: two in `tests/chat/test_scheduler.py` (they fail on their own; nothing in the chat code was touched; the likely cause is the real clock against fixed 29 Oct dates, **not confirmed**) and one Stitch-prompt check for the two new screens, which I then fixed. The Stitch, assistant, AI and papers_hub groups pass after the fix (429 passed).
- PWA: vitest 438 passed, eslint and `tsc` clean. `ruff check`, `ruff format --check` and `mypy --strict engine ai/validators` clean.
- Browser: full run 181 passed, 7 skipped, 3 failed. The demo's two failures were a stale URL assertion and a hard-coded Begin route, both fixed and re-run green (`demo.spec.ts` 3 passed); the third (`programme.spec.ts` photo history) passes alone and looks like a timing flake. I did not re-run the whole suite after those fixes.
- Two bugs the browser tests found: a status string missing in the strings table crashed the whole Papers page (now a test lists every status and reason), and a stale closure meant a first paper on a fresh phone did not appear until a reload.

## Not built, or only partly

- Duplicate as new version (Edit on a paper in use makes a new version, but there is no separate button); an Assigned card on Home; reminders; the assistant preparing an assignment draft; Generate 20 demo sheets on the Files tab.
- Exact reuse of a Paper Studio layout map on import (always "approximate"); keeping a sheet for a check (refused with a message).
- The phone scores only the pilot Forms A and B. An imported paper with other items is marked by hand with its key (`phone_form` says which).
- **Call 16 has not been run live.** The browser tests replay an authored recording (`scripts/make_paper_import_fixture.py`, labelled in the file), so there is no accuracy claim.
- Role headers are session values until real role assignment (P12): scopes hold against the server's own cohort records, not signed identities.
- The free-text assistant does not call `paper_status` yet (tools are listed, not invoked). Hindi and Tamil strings, questions and help are drafts, unreviewed.
- The privacy, integrity and judge reviewer subagents were not run.

## Edit and delete (added later)

Built as described in the DECISIONS entry "Edit and delete a paper": Edit and Delete buttons on every row and in the detail page; 8 new tests in `tests/papers_hub/test_api.py` and 2 in `apps/pwa/e2e/papers-hub.spec.ts`; `tests/papers` and `tests/papers_hub` pass (143 before the screen change). `store.freeze` now records first use on a post-test twin.
