# ASSISTANT: one assistant, scoped by role

Spec: `docs/build/Claude Code prompt one assistant, scoped by role (supersedes the judge guide pro.md`. Status 29 Oct 2026: built and tested; free-text answers by a live model not yet run.

## What is built

| Step | What | Where |
| --- | --- | --- |
| 1 | Scope matrix as data: five scopes (teacher, mentor, coach, officer, judge) with namespaces, tools, minimum count and plain scope lines | `assistant_scopes.yaml`, `services/assistant/scopes.py` |
| 2 | Server-side enforcement: the authenticated role is `judge` only in the judge deployment, else `teacher`; View as is refused for anyone else; the About tab is always the judge scope; the log holds role, scope and question id only | `services/api/assistant.py` |
| 3 | Seven namespaces built from an allowlist, with a secret, roll number, phone and email scan that fails the build; plain JSON index bundled in the image (word-based retrieval, no embeddings: decided 29 Oct) | `services/assistant/index.py`, `scripts/build_assistant_index.py`, `docs/help/*.md` |
| 4 | Deck slides and video script as sources; three citation types (file, slide, video); claims check | `scripts/extract_deck.py`, `docs/submission/slides.md`, `docs/submission/video_script.md`, `video.json`, `scripts/check_claims.py` |
| 5 | Rubric map written from the code, with an honest status per row | `docs/RUBRIC_MAP.md` |
| 6 | Questions per role (judge about 40) and a pure function that picks the same five for the same context | `docs/assistant_questions/`, `services/assistant/questions.py` |
| 7 | Answering: retrieval inside the scope, call 14 for free text, validation, abstention, teacher tone rules, pre-written judge answers that work offline, spend and rate caps | `services/assistant/answer.py`, `ai/calls/c14_assistant_answer.py`, `limits.py`, `curate.py` |
| 8 | The panel (`#/assistant`): role title, permanent scope note, five chips, free text, answer with sources, how to check and limits, footer with commit; judge-only View as, About tab and test path; a link on every screen | `apps/pwa/src/screens/Assistant.tsx`, `apps/pwa/src/lib/assistant.ts` |
| 9 | Tests: leak matrix, index allowlist and planted secrets, stable five, citations, planted instruction, no write action, caps | `tests/assistant/` |
| 10 | Evaluation by code, per role | `evals/assistant_eval.md` (generated) |
| 11 | AI_USAGE, DECISIONS, README, inventory (X29) | this commit |

## Evidence from this session

- `python -m pytest tests/assistant tests/chat`: run before this commit; the index was stale and was rebuilt with `scripts/build_assistant_index.py` (1,213 chunks).
- `scripts/check_claims.py`: 46 rows, 14 slides, 9 video segments, 0 mismatches, 0 forbidden words, 0 late claims.
- Browser (`apps/pwa/e2e/assistant.spec.ts`, 5 tests, run against the local build): the judge session sees the scope note, View as, About and the test path; a suggested question gives an answer with sources and a check line; viewing as a teacher removes the repository wording and a request for a repository file returns no file content; Hindi reads with no raw keys; no sideways scroll on a phone.

## What it does not do or has not shown

- **No live model run for call 14.** `evals/assistant_eval.md` measures the retrieval, scope, refusal and citation path with no model; the wording of a live answer is pending. Spend for it needs your go-ahead.
- **Leak probes:** nothing from outside the scope was shown in any probe (3 of 3 per role), but not every probe was refused outright (mentor, coach and officer refused 2 of 3 in the generated eval). That is counted in the eval file and was not tuned away.
- **Data tools are declared, not connected:** no tool reads live class data yet (rubric row AS.3, Roadmap). A teacher's "How is my class doing" is answered from help pages, not her counts.
- **Production has only the teacher role** until real role assignment exists.
- **Slide numbers and video times are provisional** until the final deck and video exist.

## Needs people

- **Seema or Shivani:** Hindi and Tamil questions and the role help pages (`docs/help/`) are English drafts; the Hindi and Tamil panel strings are first drafts.
- **After the final deck and video:** replace `docs/submission/deck.pptx` and `video.json` with the real files, set the timestamps in `video_script.md`, run `python scripts/extract_deck.py`, then `python scripts/build_assistant_index.py` and `python scripts/check_claims.py`. Redeploy so the image carries the new index.
