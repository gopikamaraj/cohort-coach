# UI re-skin (apps/pwa-v2), behaviour frozen

Spec: `docs/build/Claude Code prompt re-skin the front-end (design system, screenshot loop, no cha.md`. Changed by the user: the work lives in a **new folder, `apps/pwa-v2/`** (a copy of `apps/pwa/`); the original is untouched, so the `UI_V2` flag is not needed. Reference: `docs/design/reference/practice-class-v3.html`. **Parked 30 Oct 2026: `apps/pwa-v2/` is not run, deployed or extended; v1 (`apps/pwa/`) is the only front-end (DECISIONS.md).** Status 29 Oct 2026: built and checked; **not every screen is on the new components** (see "What is not done").

## What was built

| Step | What | Where |
| --- | --- | --- |
| 1 | Audit: 67 "before" renders (21 routes, 2 sizes; main screens also in Hindi and Tamil) and a rubric table of 12 defects | `docs/design/audit/before/`, `AUDIT.md`, `apps/pwa-v2/qa/audit-shots.mjs` |
| 2 | Tokens: light and dark values, five text sizes in rem, spacing, radii, elevation, motion | `apps/pwa-v2/src/styles/tokens.css` |
| 2 | Base layer: raw inputs, selects, textareas, buttons, focus ring, tables, reduced motion | `src/styles/base.css` |
| 3 | 22 components (Button, Card, Chip, StatusPill, TextField, SelectField, Toggle, Segmented, ListRow, BigNumber, ProgressMeter, Callout, EmptyState, Skeleton, Dialog, BottomSheet, Avatar, AudioPlayer, BarChart, StepFlow, Table, TopBar; Toast reused) | `src/ui/index.tsx`, `src/styles/components.css` |
| 3 | Living style guide, linked from judge mode | `#/dev/styleguide`, `src/screens/StyleGuide.tsx`, `docs/design/STYLEGUIDE.md`, inventory X30 and prompt |
| 4 | App shell: bottom bar on phones, side rail from 900 px; full-width pages; landing without an empty rail | `src/App.tsx`, `components.css` |
| 4 | Practice Class rebuilt to the reference layout: scenario card, children as cards with the speaker ringed, replies as bubbles, "your turn" column beside the class | `src/screens/Practice.tsx`, `components.css` |
| 4 | Officer cohorts form and Profile fields moved to the shared field layout | `components/OfficerCohorts.tsx`, `components.css` |
| 6 | Transitions of 200 ms or less, skeleton and empty-state components, inline SVG art | `components.css`, `src/ui` |
| 7 | New browser checks, axe runs, Lighthouse, bundle sizes | below |

Behaviour is unchanged: no API, state, permission or AI-call code was edited. Practice.tsx gained wrapper elements only; every `data-testid` is kept.

## Screenshot loop (what I looked at and fixed)

| Screen | Defects found in the images | Fixed |
| --- | --- | --- |
| Officer cohorts | default grey select, inputs and button, no spacing | form grid with labelled fields and a filled button |
| Profile | add-class box collapsed to a sliver | field and button share a row |
| Practice (two passes) | one column on a laptop; children wrapped to 3+2 on a phone; narrow compose box in the side column; counter touching cards | two columns from 1024 px; five children in one row on a phone; stacked compose box; spacing |
| Landing | empty side rail; header not lined up with the page column | rail hidden when there are no tabs; strip padding aligned |

Final images: `docs/design/audit/after/` (66 renders plus `practice_*` files). Defects I did **not** fix are under "What is not done".

## Numbers (from files, not typed)

| Check | Before (`apps/pwa`) | After (`apps/pwa-v2`) | Source |
| --- | --- | --- | --- |
| Gzipped JS + CSS | 242,632 bytes | 250,105 bytes (+3.1%; limit +15%) | built `dist/assets`, measured with gzip |
| axe (WCAG A, AA, 2.1 AA, best practice; 21 routes, light and dark, 360 and 1280) | 16 findings (region 4, scrollable-region-focusable 4, label 4, empty-table-header 4) | 0 findings on the 21 original routes; style guide 0 after an avatar fix | `qa/axe.mjs`; JSON kept in `docs/design/audit/` |
| Lighthouse mobile, `/#/home`, simulated throttling | performance 94, accessibility 100, best practices 100 | performance 94, accessibility 100, best practices 100 | `lh_before.json`, `lh_after.json` (Lighthouse 12 has no PWA score) |
| Sideways scroll | 0 of 66 renders | 0 of 66 renders; also 6 browser tests (en, hi, ta at 360 and 1280) | `metrics.json`, `e2e/reskin.spec.ts` |
| Tap targets under 44 px (buttons, links, selects) | 5 routes | checkboxes remain 24 px but their whole label is a 44 px target; test passes for buttons and links | `e2e/reskin.spec.ts` |
| Distinct font sizes on one screen | up to 7 | at most 5 | `metrics.json` |
| Unit tests | 375 pass | 375 pass; lint clean; typecheck clean | vitest, eslint, tsc |
| Browser suite | n/a | 12 new tests pass; of the original 149, 137 passed, 7 skipped, 5 failed on first run; see below | `npx playwright test` |

The 5 first-run failures: two are **not caused by the re-skin** (they fail on the original app too: the Assistant scope line for a teacher now contains the word "repository", and the AI map now lists 13 calls where the test expects 10; both are the earlier assistant and call 12 to 14 work). Three were the re-skin's doing and are fixed or updated: a real overflow at 768 px on Practice (fixed in CSS); the "four tabs and More" test counted hidden rail tabs (now counts visible ones); and the "teacher screens sit in a phone-sized column" test is replaced, because full width is the new design (a decision, logged). After the fixes, those three specs pass (16 of 18 in the re-run; the other 2 are the pre-existing ones).

## Checks of the quality gates in the prompt

- **Keyboard:** scrollable tables are reachable; the Dialog uses the native element (focus trap, Escape). Focus ring is 3 px on every control.
- **Reduced motion:** tested (transition duration under 10 ms).
- **Offline:** the style guide reloads with the network off after the first load (tested).
- **Dark mode:** follows the phone; tested body colour; axe finds no contrast failure in dark.
- **Languages:** Hindi and Tamil fit in all main screens; a test adds 30 percent to every text node and checks there is no sideways scroll.

## What is not done (honest list)

1. **Most of the 13 screens are re-skinned through shared classes, not rebuilt on `src/ui` components.** Fully reworked: Practice Class, Officer cohorts, Profile classes, the shell. The rest keep their old markup with the new tokens, fields and cards. Moving each to components is future work.
2. **Practice Class reference match is structural, not pixel exact.** Missing against `practice-class-v3.html`: the board of blocks (tens rods and ones), the waveform around the mic button, the quick-move pills with icons, the coaching-feedback cards with the "following" meter. Those belong to the live feature set (materials and feedback already exist as other sections), not to this skin.
3. **Fonts:** the app still uses system fonts (CLAUDE.md rule 18 wants self-hosted Inter, Noto Devanagari and Noto Tamil). Not changed here; the size would break the bundle budget without subsetting.
4. **Visual snapshot tests:** none stored. The loop compares by eye and by measured metrics.
5. **App icon and splash:** unchanged.
6. **Hindi and Tamil strings on the new style-guide link are drafts** for Shivani and Gopi.
7. **Judge-mode screens other than Practice were not checked at 200 percent text size.**
8. Practice screenshots were taken against a live API for the first passes (one typed turn; a few cents); the suite and final shots use the recorded API.

## Decisions and open question

Logged in `docs/build/DECISIONS.md` (2026-10-30, re-skin in a new folder). Open: whether v2 replaces `apps/pwa/` for the final deploy. To try it: `run-frontend-v2.bat` serves http://localhost:5174 next to the original on 5173.
