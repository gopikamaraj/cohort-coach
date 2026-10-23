# Stitch prompts report

Date: 2026-10-23. Task: ready-to-paste Google Stitch prompts for every screen and feature, under `docs/design/stitch/`. Design work only: nothing in `services/` or `apps/` was touched for this task.

## What was produced

| Item | Where | Count or note |
| --- | --- | --- |
| Theme | `docs/design/stitch/DESIGN.md` | Created: it was missing (flagged below) |
| Shared header | `docs/design/stitch/_header.md` | 242 words (limit 250) |
| Inventory | `docs/design/stitch/INVENTORY.md` | 45 rows: 13 design-doc screens, 28 added (X1 to X28), 4 roadmap cards (R1 to R4) |
| Prompts | `docs/design/stitch/prompts/<ID>-<slug>.md` | 45 files, 688 to 1,133 words each (limit 600 to 1,500); 36,569 words in all |
| Telegram | `docs/design/stitch/TELEGRAM-MESSAGES.md` | Five message groups with Hindi and Tamil button labels marked as needing Shivani |
| Guide | `docs/design/stitch/README.md` | Generation order, theme import, export convention, review checklist, tracking table |
| Checker | `scripts/check_stitch_prompts.py`, `tests/test_stitch_prompts.py` | 16 tests; one failing case per rule |
| Kit | `CLAUDE.md` rule 18; `BUILD_PROMPTS.md` Design reference lines in P05 to P12 and P16; `DECISIONS.md` 2026-10-23; `PROGRESS.md` | |

By role: Teacher 24, Programme officer 7, Judge 6, Coach 4, Mentor 3, Admin 1.

Commands run: `python scripts/check_stitch_prompts.py` prints OK for 45 prompts; `pytest tests/test_stitch_prompts.py` 16 passed.

## Screens added (no screen in the design doc's 13)

X1 Landing page and role picker · X2 Guided tour · X3 Practice Class Watch · X4 Try with hints and Try to break it · X5 AI map, AI layers and audit trail · X6 Welcome, language and consent · X7 Check entry: photo capture and confirm · X8 Where it most likely went wrong (stage lines) · X9 Practice feedback and rehearsal review · X10 After you try it in class · X11 Lesson card and model run · X12 Tap reply, voice reply and silence states · X13 Cohort chat · X14 My programme · X15 What I entered · X16 My profile and data · X17 Privacy notice · X18 Tell us what you think · X19 Admin feedback review · X20 Mentor dashboard · X21 Coach home · X22 Cohort page and moderation · X23 Content library · X24 Scenario page · X25 Role assignment and weekly batch · X26 CRC visit brief · X27 Materials tray and avatar expressions · X28 Chat steps.

Roadmap cards: R1 Child twin · R2 Grade handoff · R3 Names on this phone · R4 Beyond Grade 3 maths (topic packs, WhatsApp, lesson videos).

## Where the specification was ambiguous or the brief and the repo disagree

1. **Child twin, grade handoff and on-device name mapping are not in the repo.** The brief names them; nothing defines them, and the privacy rules say no child names are collected. R1 to R3 are locked roadmap cards with a `TODO-HUMAN(Gopi)` line each. Confirm the one-line promises before anyone designs further. R4 comes from the parked roadmap items.
2. **"Improvement track (voice-note slots, tap reply, voice reply, silence states)".** "Voice-note slots" is not defined in the repo. The feature maps to T4, X11 (lesson card) and X12 (taps, voice reply, silence).
3. **One tap versus two taps.** The brief lists one set of buttons (Tried it, Partly, Not yet). The repo ships two taps (Tried it in class: Yes or Not yet; then How did it go: Worked, Partly, Didn't work). `TELEGRAM-MESSAGES.md` shows the shipped version and the brief's variant; Gopi decides.
4. **P3 Review queue.** The design doc gives it to the programme officer; later decisions make the coach the reviewer and the officer the one who switches it on. P3 is one screen with two keys.
5. **Dark theme.** The brief gives light colours only. The dark values in `DESIGN.md` were derived and need a designer's check.
6. **"Asha-says line".** Asha is also one of the simulated children in the dataset, so the shared header says "child-says line"; the checker forbids child names in the header and in every prompt outside the Practice Class (T5, X3).
7. **Fonts and touch targets.** `CLAUDE.md` said system fonts only and tap targets of at least 48 px. The direction uses Inter and the Noto fonts and 44 px (48 for primary buttons). Logged in `DECISIONS.md`; existing screens keep 48 px until rebuilt, and the self-hosted font files still need a data-budget measurement (P14).
8. **Illustrative numbers.** Class and cohort values come from the generated data: the demo class (28 children, 11 take the smaller digit from the larger), the block (40 schools, 120 classes, cohorts of 9 teachers in 7 schools), the error map counts by medium, the verdict table (`docs/evidence/demo_verdicts.md`) and one class's fall (20 of 32 to 10 of 32). The stage-line counts in X8 other than the first line, the cohort chat and the profile figures are layout examples and say so where they appear.
9. **Stale string in the repo (not changed here).** `judge.step3` still says "try the keypad", but the check screen now uses the phone's number keyboard. J1's prompt says "type the answers".

## Needs people

- **Shivani:** the Hindi and Tamil labels and messages in `TELEGRAM-MESSAGES.md` and the Hindi and Tamil strings quoted in the prompts (the brief names Shivani for both; the repo's convention has Gopi reviewing Tamil).
- **Seema:** confirm the stage wording shown in X8 and the concept grouping of the worksheet (place value, addition with carrying, subtraction with borrowing).
- **Gopi:** the open points above (R1 to R3, the one-tap variant, the font budget); generating the screens in Stitch and exporting them to `docs/design/stitch/exports/<ID>/` (not done: it needs a Stitch account).

## Not done

- No screen has been generated in Stitch or exported; the tracking table in `README.md` shows every row as Prompt ready.
- The UI was not rebuilt; that waits for the exports.
