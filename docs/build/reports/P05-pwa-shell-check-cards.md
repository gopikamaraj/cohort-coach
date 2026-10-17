# P05 · PWA shell, judge mode, check entry, error cards — report

**Status:** ✅ · **Dates:** 2026-10-17 → 2026-10-17 · **Commits:** `5cbe187`…(this report) · **Gate:** none

## Summary

An installable, offline-first PWA in English, Hindi and Tamil. Judge mode opens with no login: a role switcher, a language switcher, a simulated-data banner, a five-minute test script with deep links, "Advance to Term 2", "Simulate offline", and links to the raw AI map and audit trail. A teacher enters a check on a keypad (blank and can't-read marks, autosave), the phone diagnoses it with the engine's answer keys, and the error cards show counts with an example from her own class's answers and the stick-bundle drawing. Per-child answers never leave the phone; only class-level counts are queued and sent, and the server rejects anything else. The whole teacher path works offline after the first load.

## What was built

| Area | Files | Notes |
| --- | --- | --- |
| Design system | `docs/design-system.md`, `apps/pwa/src/styles.css`, `tests/test_design_tokens.py` | Notebook, blue ink, tally bundles; contrast recomputed from the CSS by a test |
| i18n | `apps/pwa/src/i18n/{en,hi,ta}.json`, `index.ts`, `scripts/i18n.py` | Typed keys, English fallback, CSV export and import, to-do list |
| Client core | `lib/{db,sync,check,cards,demo,net,router}.ts`, `state.tsx` | IndexedDB tables, queue, hash router, forced-offline switch |
| Screens | `screens/{Judge,Home,Check,Cards}.tsx`, `components/parts.tsx`, `App.tsx` | J1, T1, T2, T3; phone frame at 768 px and up |
| PWA | `vite.config.ts`, `public/icon-*.png`, `scripts/make_icons.py` | Manifest with 192, 512 and maskable icons; Workbox precache; `/api` never cached |
| Server | `services/api/profiles.py`, `db.py` (`ProfileSync`), `engine/export_keys.py` | `POST /api/classes/{id}/profile` (counts only, `extra=forbid`), `GET /api/demo/block` |
| Tests | `src/**/*.test.ts` (167), `e2e/app.spec.ts` (9), `tests/api/test_profiles.py`, `tests/test_pwa_scripts.py` | |
| Budget and evidence | `scripts/bundle_size.py`, `scripts/lighthouse_summary.py`, `e2e/screenshots.spec.ts`, `docs/offline.md` | `python tasks.py bundle`, `python tasks.py e2e`, CI steps added |

## Acceptance

| Criterion | Proof | Key output | Status |
| --- | --- | --- | --- |
| Installable and works offline after first load for T1–T3 | `e2e/app.spec.ts` "is installable" and "works offline after the first load" | active service worker; manifest with 192, 512 and maskable icons; offline reload reaches Home, Enter check and My class | ✅ |
| T3 never shows a percentage; simulated banner on synthetic data; languages switch at runtime | `e2e/app.spec.ts` (no `%` in the page text, banner, runtime switch en → hi → ta → en); `i18n.test.ts` (no percentage word in any string); `flow.test.ts` | pass | ✅ |
| Bundle under budget | `python tasks.py bundle` → `docs/evidence/bundle_size.json` | initial JS 112,504 bytes compressed (fail above 1,000,000, warn above 400,000) | ✅ |

## Tests and evals

| Suite | Count | Result | Source |
| --- | --- | --- | --- |
| Vitest | 167 | pass | `python tasks.py test` |
| Playwright | 9 (+4 evidence screenshots on demand) | pass | `python tasks.py e2e` |
| pytest (all) | see `python tasks.py check` | pass | `python tasks.py check` |

Evidence for judges: `docs/evidence/bundle_size.json`, `docs/evidence/lighthouse_mobile.json` (Lighthouse mobile profile, one run: performance 99, accessibility 100, best practices 100; directional), screenshots in en, hi, ta at 360 px and the desktop frame in `docs/evidence/screenshots/`. The numbers table is `docs/evidence/numbers.md`.

## AI calls touched

None. P05 has no AI call; the error cards are made by code from the engine's answer keys.

## Cost and latency measured

No AI spend. Lighthouse mobile (emulated phone, simulated slow 4G, CPU slowed 4×): see the evidence file. Not Slow 3G and not a real low-end phone: both are still to do in P14.

## Deviations and decisions

| What changed | Why | DECISIONS |
| --- | --- | --- |
| Operands (`a`, `b`) added to the answer keys | to show a class's own example | "P05 PWA decisions" |
| Untracked pattern counted per answer, card says "answers" | the engine counts answers, not children | same |
| The "this is wrong" flag is kept on the phone, and the card says so | no server endpoint yet; the cards are code-made | same; `docs/offline.md` |
| Server accepts only the random class id the app makes | privacy review | same |
| Lighthouse has no PWA score (v12+) | installability asserted by Playwright | same |
| Tests were written alongside the code, not strictly before for the API and screens | speed; contract tests (counts-only, offline) exist and pass | noted here |

## Reviews

| Reviewer | Verdict | Blocking findings fixed | Open non-blocking |
| --- | --- | --- | --- |
| judge-reviewer | pass with fixes | flag text now says it is kept on the phone; payload size asserted under 2 KB | judge links need `/api` routed in staging (P15); judge steps 1 and 5 have no deep link; Slow 3G and real-phone runs (P14); no user test of the keypad yet |
| privacy-guardian | clear | server class id restricted to the app's random id | flag sender must keep `{card, term}`; empty the photo outbox after reading (P08) |
| integrity-auditor | honest with fixes | contrast ratios now recomputed from the CSS by a test; unmeasured payload phrase removed | DECISIONS entry awaits Gopi |

## Waiting on people

| Owner | Item | Placeholder in place | Needed by |
| --- | --- | --- | --- |
| Shivani | Review the Hindi strings (`apps/pwa/src/i18n/hi.json`) via `python scripts/i18n.py export` | yes (build draft) | P06 |
| Gopi | Review the Tamil strings (`ta.json`); confirm the P05 DECISIONS entry | yes | P06 |
| Seema | Try the keypad check entry with a teacher; feed `docs/feedback-log.md` | n/a | test round 3 |

## Judged areas served

Real scenarios: offline-first, queued sync, small bundle, three languages, system fonts. Ease of use: one action per screen, large keypad, counts a teacher can read at a glance. The demo link: judge mode opens with no login.
