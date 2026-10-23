# Stitch prompts for Cohort Coach

Ready-to-paste prompts for Google Stitch, one per screen, built from the repo. This is design work only: nothing here changes `services/` or `apps/`.

## Files

- `DESIGN.md`: the theme (Calm Institutional Material, Material 3): colour, shape, type, layout, component names.
- `_header.md`: the shared block every prompt inlines at the top.
- `INVENTORY.md`: every screen with ID, role, device priority, source and features.
- `prompts/<ID>-<slug>.md`: one self-contained prompt per screen.
- `TELEGRAM-MESSAGES.md`: the teacher's Telegram messages as text mockups (Telegram is not a Stitch screen).
- `exports/<ID>/`: where Stitch exports are kept (see below).

## Generation order

1. T1 to T6 (teacher path, phone first). Practice Class (T5) is already approved: generate it first and use it as the style anchor, then ask Stitch to match it for every other screen.
2. M1, M2 and X20 (mentor).
3. P1 to P4 (programme officer), then the coach and library screens X21 to X26.
4. J1 and the judge screens X1 to X5.
5. The remaining X screens in the order of the tracking table, then the roadmap cards R1 to R4.

## Import DESIGN.md as the theme

1. In Stitch, open the project settings and choose the theme or design-system import.
2. Paste the colour tokens and the type and shape rules from `DESIGN.md` (or upload the file if your Stitch version accepts it).
3. Set Inter as the font; add Noto Sans Devanagari and Noto Sans Tamil as fallbacks.
4. Generate T5 first; check it matches the approved Practice Class; only then generate the others.

## Export convention

Save each export as `docs/design/stitch/exports/<ID>/screen.png` and `code.html`. Where a mobile variant exists, add `screen-mobile.png` and `code-mobile.html`. Build the UI from these exports. Stitch's code export has two known bugs: it packs three fonts into one malformed Google Fonts URL, so Inter never loads, and it loads Tailwind from a CDN. Never copy either into our code: use our own CSS, self-hosted subsetted fonts and inline SVG icons.

## Review checklist (per screen)

- The header fits at 360px without clipping (two rows on a phone).
- Inter renders (not a fallback serif or system font).
- Every touch target is at least 44px; primary buttons 48px; inputs 56px.
- Teacher screens show counts, never percentages.
- No child names outside the Practice Class.
- Every icon is paired with text.
- Tamil and Hindi strings fit at 30 percent longer.
- One primary action per teacher screen; every teacher text card has a play button.
- No gradients, blurs, emojis or shadows.
- Meaning is never by colour alone.

## Tracking

| Order | ID | Screen | Prompt | Status | Exported | Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | T1 | Home | prompts/T1-home.md | Prompt ready | | |
| 2 | T2 | Check entry | prompts/T2-check-entry.md | Prompt ready | | |
| 3 | T3 | What my class gets wrong | prompts/T3-what-my-class-gets-wrong.md | Prompt ready | | |
| 4 | T4 | My track | prompts/T4-my-track.md | Prompt ready | | |
| 5 | T5 | Practice Class | prompts/T5-practice-class.md | Prompt ready | | |
| 6 | T6 | Next term | prompts/T6-next-term.md | Prompt ready | | |
| 7 | M1 | Invitation and method capture | prompts/M1-invitation-and-method-capture.md | Prompt ready | | |
| 8 | M2 | Cohort digest | prompts/M2-cohort-digest.md | Prompt ready | | |
| 9 | X20 | Mentor dashboard | prompts/X20-mentor-dashboard.md | Prompt ready | | |
| 10 | P1 | Error map | prompts/P1-error-map.md | Prompt ready | | |
| 11 | P2 | Cohorts | prompts/P2-cohorts.md | Prompt ready | | |
| 12 | P3 | Review queue and two-key approval | prompts/P3-review-queue.md | Prompt ready | | |
| 13 | P4 | Track results | prompts/P4-track-results.md | Prompt ready | | |
| 14 | J1 | Judge mode | prompts/J1-judge-mode.md | Prompt ready | | |
| 15 | X1 | Landing page and role picker | prompts/X1-landing-and-role-picker.md | Prompt ready | | |
| 16 | X2 | Guided tour | prompts/X2-guided-tour.md | Prompt ready | | |
| 17 | X3 | Practice Class: Watch two rehearsals | prompts/X3-practice-watch.md | Prompt ready | | |
| 18 | X4 | Try with hints and Try to break it | prompts/X4-hints-and-try-to-break-it.md | Prompt ready | | |
| 19 | X5 | AI map, AI layers and audit trail | prompts/X5-ai-map-and-audit.md | Prompt ready | | |
| 20 | X6 | Welcome, language and consent | prompts/X6-welcome-language-and-consent.md | Prompt ready | | |
| 21 | X7 | Check entry: photo capture and confirm | prompts/X7-check-photo-capture.md | Prompt ready | | |
| 22 | X8 | Where it most likely went wrong | prompts/X8-where-it-went-wrong.md | Prompt ready | | |
| 23 | X9 | Practice feedback and rehearsal review | prompts/X9-practice-feedback-and-review.md | Prompt ready | | |
| 24 | X10 | After you try it in class | prompts/X10-after-you-try-it-in-class.md | Prompt ready | | |
| 25 | X11 | Lesson card and model run | prompts/X11-lesson-card-and-model-run.md | Prompt ready | | |
| 26 | X12 | Tap reply, voice reply and silence states | prompts/X12-tap-reply-and-voice-reply.md | Prompt ready | | |
| 27 | X13 | Cohort chat | prompts/X13-cohort-chat-teacher.md | Prompt ready | | |
| 28 | X14 | My programme | prompts/X14-my-programme.md | Prompt ready | | |
| 29 | X15 | What I entered | prompts/X15-what-i-entered.md | Prompt ready | | |
| 30 | X16 | My profile and data | prompts/X16-my-profile-and-data.md | Prompt ready | | |
| 31 | X17 | Privacy notice | prompts/X17-privacy-notice.md | Prompt ready | | |
| 32 | X18 | Tell us what you think | prompts/X18-tell-us-what-you-think.md | Prompt ready | | |
| 33 | X19 | Admin: feedback and simulation reports | prompts/X19-admin-feedback-review.md | Prompt ready | | |
| 34 | X21 | Coach home | prompts/X21-coach-home.md | Prompt ready | | |
| 35 | X22 | Cohort page and moderation | prompts/X22-cohort-page-and-moderation.md | Prompt ready | | |
| 36 | X23 | Content library | prompts/X23-content-library.md | Prompt ready | | |
| 37 | X24 | Scenario page | prompts/X24-scenario-page.md | Prompt ready | | |
| 38 | X25 | Role assignment and weekly batch | prompts/X25-role-assignment-and-weekly-batch.md | Prompt ready | | |
| 39 | X26 | CRC visit brief | prompts/X26-crc-visit-brief.md | Prompt ready | | |
| 40 | X27 | Materials tray and avatar expressions | prompts/X27-materials-tray-and-avatar-expressions.md | Prompt ready | | |
| 41 | X28 | Chat steps (same flows as the bot) | prompts/X28-chat-steps.md | Prompt ready | | |
| 42 | R1 | Roadmap card: child twin | prompts/R1-roadmap-child-twin.md | Prompt ready | | |
| 43 | R2 | Roadmap card: grade handoff | prompts/R2-roadmap-grade-handoff.md | Prompt ready | | |
| 44 | R3 | Roadmap card: names on this phone | prompts/R3-roadmap-name-mapping.md | Prompt ready | | |
| 45 | R4 | Roadmap card: beyond Grade 3 maths | prompts/R4-roadmap-beyond-grade-3-maths.md | Prompt ready | | |

Status values: Prompt ready; Generated; Exported; Reviewed; Built.

## Checker

`python scripts/check_stitch_prompts.py` fails unless every ID in `INVENTORY.md` has a prompt, every prompt carries the shared header, no emoji appears, no child name appears outside the Practice Class prompts, teacher-facing prompts have no percent sign, and every file is within 600 to 1,500 words.
