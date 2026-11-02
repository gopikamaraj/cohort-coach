# UI audit: the original front-end (`apps/pwa/`), before the re-skin

Rendered with `apps/pwa-v2/qa/audit-shots.mjs` against the built original app (judge API, simulated data): 21 routes at 360×800 and 1280×800 in English, and the six main screens in Hindi and Tamil. 67 files in `before/` (`metrics.json` holds the measured numbers). The re-skinned set is in `after/`.

Measured, not judged by eye (from `before/metrics.json`):

| Measure | Before |
| --- | --- |
| Screens with sideways scroll | 0 of 66 renders |
| Screens with a tap target under 44 px | 5 routes (practice 1, profile 6, watch 1, cohort 1, officer 3) |
| Distinct font sizes on one screen | up to 7 (officer), 6 (profile); the five-size target was missed on 2 routes |

## Defects against the visual rubric

Severity: **high** blocks use or looks broken; **medium** is inconsistent; **low** is polish.

| # | Screen | Rubric item | Defect | Sev. |
| --- | --- | --- | --- | --- |
| 1 | Officer (cohorts) | consistent controls | The "Start a cohort" form shows the browser's default select, inputs and a grey button: labels glued to the fields, no spacing. | high |
| 2 | Profile (My classes) | consistent controls; touch targets | The "add a class" text box collapses to a 25 px sliver beside a full-width button. | high |
| 3 | All phone screens | short copy; Hindi/Tamil fit | Bottom-bar labels are cut ("Enter c…"). | medium |
| 4 | All teacher screens | one alignment grid | Before the width fix, teacher and mentor screens sat in a 440 px column on a laptop while coach and officer screens were full width. | high (fixed in `apps/pwa` the same day) |
| 5 | Landing | hierarchy | Role, language and mode are three bare selects above the page, with no labels on screen and the same weight as the page title. | medium |
| 6 | Home, Check, Practice | primary action | On a wide screen the primary button stretches to the full width, so it reads as a bar, not a button. | medium |
| 7 | Officer, Profile | type scale | Seven and six font sizes on one screen. | medium |
| 8 | Profile, Practice, Watch, Cohort | touch targets | Check boxes are 24 px; the label is not a larger target. | medium |
| 9 | Several | colours from tokens | Colours were already tokens; there was no dark mode. | low |
| 10 | Officer funnel | sensible amount | Funnel lines are plain paragraphs with the source label in small print; hard to scan. | low |
| 11 | All | states | Loading states are text only (no skeletons); empty states are one grey line. | low |
| 12 | Profile, Admin, History, Privacy, AI map | keyboard access | Scrollable table wrappers could not be reached by keyboard. | medium |

What was already fine: spacing and cards follow the tokens, icons are line icons with text, Hindi and Tamil never scrolled sideways, copy is short.
