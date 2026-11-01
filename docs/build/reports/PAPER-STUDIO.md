# Report: Paper Studio

Date: 2026-10-30. Source prompt: `docs/build/Claude Code prompt Paper Studio (rule-based worksheet generator, rule database,.md`. Scope chosen by Gopi: core and main screens.

## What was built

| Step | What | Where | Tests |
| --- | --- | --- | --- |
| 1 Rule database | Tables `rule_version`, `rule_template`, `rule_bug`, `blueprint`, `blueprint_slot`, `string_pack`, `paper`, `paper_item`, `class_profile`, `review_queue`, `paper_event`; version 1 seeded from the engine and the pilot pack; YAML export | `services/papers/models.py`, `services/papers/rules.py`, `services/papers/store.py`, `rules/paper-rules.v1.yaml` | `tests/papers/test_store.py` |
| 2 Generator | Seeded (never the global random state), anchors with fixed skill and difficulty, adaptive items by class weight that skip skills not assessed, discrimination, coverage (at least two items per error, or a failure that names the rule), uniqueness, Form B twin with no repeated number pair, stable hash | `services/papers/generator.py` | `tests/papers/test_generator.py` |
| 3 Class profile | Last check's class counts, else the intake form (a topic not taught is not assessed), else the standard paper; a pre-test makes its frozen twin | `services/papers/store.py`, `apps/pwa/src/components/PaperMaker.tsx` | `tests/papers/test_store.py`, `apps/pwa/src/lib/papers.test.ts` |
| 4 Approval | Auto-approval only within the rules, spot check one in five, custom and failing papers to the queue, failing papers cannot be approved, rejection keeps its reason, freeze on first sheet | `services/papers/store.py`, `services/papers/models.py` | `tests/papers/test_store.py`, `tests/papers/test_papers_api.py` |
| 5 Verifier | Independent of the generator and the engine (its imports are tested): keys, wrong answers, coverage, discrimination, duplicates, twins, strings, glyphs in the embedded fonts, overflow and overlap | `services/papers/verifier.py` | `tests/papers/test_verifier.py` (catches a deliberately broken key) |
| 6 PDF | WeasyPrint, A4, black and white, Noto Sans, Noto Sans Devanagari and Noto Sans Tamil embedded; English, Hindi, Tamil and English and Hindi; answer key PDF; layout map in millimetres; pages looked at as images before the screens were built | `services/papers/render.py`, `services/papers/fonts/` | `tests/papers/test_render.py` (fonts embedded, layout map checked by sampling pixels) |
| 7 Screens | Papers (teacher list; coach queue and rules), Print a paper inside Start a check with the intake form, preview, key, coverage grid, anchor and adaptive labels | `apps/pwa/src/screens/Papers.tsx`, `apps/pwa/src/components/PaperView.tsx`, `apps/pwa/src/components/PaperMaker.tsx` | `apps/pwa/e2e/papers.spec.ts` (with axe) |
| 8 Integration | The pilot paper attaches to the check (code in the check header) and freezes on the first entry; events logged with class, check, blueprint, versions, seed and hash; help for teacher, coach and judge; sample PDFs | `apps/pwa/src/screens/Check.tsx`, `services/papers/store.py`, `docs/help/`, `docs/samples/` | `apps/pwa/e2e/papers.spec.ts` |
| 10 Evidence | 200 papers per language layout with their twins through every check, counts only | `scripts/paper_studio.py` | `docs/evidence/paper_studio_verification.md` |

## Differences from the prompt

- The pilot paper has 10 items, not 15; the blueprints are `baseline_10` and `standard_10_5`.
- Version 1 is recorded as approved by the pilot pack (what the team already approved); the Hindi short labels and all Tamil wording are drafts waiting for a reader, so Hindi and Tamil papers go to the review queue.
- The rule editor is a read-only view (templates, history with changes, YAML export, Test these rules); edits go through the API with the two-person rule.
- The sheet reader's code check, phone entry of a new paper's answers, and the tour step are parked (`docs/build/PARKING.md`).

## Human checks

- Hindi labels on the paper and the screens: Seema, Shivani. Tamil: Gopi. Until then those papers wait for a reviewer.
- Seema: check the anchor difficulties and the adaptive templates (ones digit zero when borrowing; answer ending in zero when carrying) against the NCERT Grade 3 book.
