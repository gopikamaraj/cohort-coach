# P06 · Practice Class UI, AI-layers overlay, audit viewer, staging — report

**Status:** 🟡 built and tested; the staging URL and the real-phone check are blocked on hosting accounts (Gopi) · **Dates:** 2026-10-17 → 2026-10-17 · **Commits:** `0aa4140`…(this report) · **Gate:** "Staging live for test round 3": **not passed**, blocked

## Summary

Teachers can rehearse in text on a phone: five original SVG children, a materials tray, a text box, a turn counter, a private feedback card with her own words highlighted, thumbs per point, a flag, and "try again with the same children". Judges get a **Show AI layers** panel under each reply, an **AI map** (8 calls by 5 layers) and an **Audit trail** (the last 50 AI calls, metadata only), all driven by the API's own trace. Degraded states are visible: a slow or failed model call gives a template reply with a notice, a spent budget shows "Practice is paused" with a recorded sample to watch, offline says so and sends nothing. The transcript stays on the phone. The staging deploy is a written recipe with a `Dockerfile` and CORS locked to the PWA's origin; it has **not** been run because there are no hosting accounts yet. The round 3 kit is ready for Seema.

## What was built

| Area | Files | Notes |
| --- | --- | --- |
| Practice screen | `apps/pwa/src/screens/Practice.tsx`, `components/practice.tsx`, `lib/practice.ts` | Transcript, ratings and flag in IndexedDB only |
| Judge views | `screens/AiMap.tsx`, `screens/Audit.tsx`, `LayersPanel` | Judge role only; audit as stacked cards (readable at 360 px) |
| Entry and seats | `screens/Home.tsx`, `Practice.tsx` | Class counts (never child answers) seat the children |
| API | `services/api/practice.py` (returns `seed`), `main.py` (CORS to `PWA_ORIGIN`), `profiles.py` | |
| Degraded states | `Practice.tsx`, `public/sample-practice.json`, `scripts/make_sample_practice.py` | Slow, paused, offline |
| i18n | `src/i18n/*.json` (65 new strings in en, hi, ta) | Hindi and Tamil are drafts |
| Tests | `e2e/practice.spec.ts` (9), `src/lib/practice.test.ts`, `tests/api/test_cors.py`, `tests/practice/test_api.py` (log canary), `tests/test_round3_summary.py` | API runs in recorded mode on its own port |
| Staging recipe | `docs/deploy.md`, `Dockerfile`, `.dockerignore`, `pyproject.toml` (`prod` extra) | Not yet run |
| Round 3 kit | `docs/user-testing/round3-script.md`, `round3-results-template.csv`, `scripts/round3_summary.py` | SUS scored by code; Hindi lines are drafts |
| Evidence | `docs/evidence/screenshots/en-5…9`, `hi-5`, `ta-5` | Taken in recorded mode (replay times), labelled so in `docs/practice-class.md` |

## Acceptance

| Criterion | Proof | Key output | Status |
| --- | --- | --- | --- |
| On a real phone over mobile data, the staging URL runs a text rehearsal end to end (human confirms) | needs hosting accounts and a phone | `docs/deploy.md` is the recipe; nothing deployed | ⛔ human |
| The overlay matches the API trace; server logs contain no transcript text | `e2e/practice.spec.ts` "the AI-layers overlay matches the API trace" (panel text equals the intercepted API JSON), "the server request log holds no transcript text"; `tests/practice/test_api.py::test_no_log_record_at_any_level_holds_what_she_typed` (all loggers at debug, canary phrase) | pass | ✅ |
| Round 3 materials ready for Seema | `docs/user-testing/` | script, consent lines, SUS (en, hi draft), results template, summary script | ✅ |

## Tests and evals

| Suite | Count | Result | Source |
| --- | --- | --- | --- |
| Vitest | 176 | pass | `python tasks.py test` |
| Playwright | 18 (+7 screenshot specs on demand) | pass | `python tasks.py e2e` |
| pytest (all) | 519 | pass | `python tasks.py check` |
| Bundle | initial JS 120,849 bytes compressed | within budget | `docs/evidence/bundle_size.json` |

No AI eval was added in P06. Text-turn latency is unchanged from P04 (over target; plan in `docs/practice-class.md`).

## AI calls touched

None changed. The screen calls the P04 API; the overlay and audit viewer only display what calls 1, 2, 3 and 7 already record.

## Cost and latency measured

No live spend in P06 (all tests run in recorded mode). Real latency and cost per turn are in `evals/results/practice_latency.json` (P04).

## Deviations and decisions

| What changed | Why | DECISIONS |
| --- | --- | --- |
| Staging not deployed | no hosting accounts or secrets yet | "P06 Practice Class UI decisions" |
| The share-session toggle only stores her choice | no sharing flow until P11 | same |
| API tests run on port 8011 with their own log | a dev server on 8000 was already running and had old code | same |
| Audit as cards, not a table | a table was cut off at 360 px (judge review) | noted here |
| Tests were written alongside the code | speed; the recorded-API suite covers the acceptance claims | noted here |

## Reviews

| Reviewer | Verdict | Blocking findings fixed | Open non-blocking |
| --- | --- | --- | --- |
| judge-reviewer | pass with fixes | PROGRESS now says staging is blocked; audit page as stacked cards; overlay screenshot shows all five layers; Tamil note and parking item | live-mode screenshots and measured MB per rehearsal after staging; a code-generated latency median in the deck |
| privacy-guardian | clear with fixes | `.dockerignore` excludes `data/pilot`, `data/private`, `.env.*`, logs; Dockerfile copies only `data/synthetic` | note the returned `seed` in `docs/privacy.md`; production flag or rate limit for `/api/judge/audit` (parked) |
| integrity-auditor | honest with fixes | log test strengthened (application logs at debug with a canary); test for thumbs, flag and the share default added; Hindi consent marked draft; test claims cited | DECISIONS entry awaits Gopi |

## Waiting on people

| Owner | Item | Placeholder in place | Needed by |
| --- | --- | --- | --- |
| Gopi | Hosting accounts and secrets; follow `docs/deploy.md`; put the URLs in PROGRESS | recipe only | test round 3 (21–25 Oct) |
| Seema | Run round 3 with `docs/user-testing/round3-script.md` (a laptop with a hotspot works until staging is up); enter results in `round3-results.csv` | kit ready | 21–25 Oct |
| Shivani | Review the Hindi consent, SUS and UI strings | drafts | round 3 |
| Gopi | Tamil round 3 script (parked) | English with a Tamil-speaking facilitator | optional |

## Judged areas served

AI use in layers (the hero, visible): the overlay, the AI map, the audit viewer. Guardrails (visible): badges on every reply and card, the checker's verdict and the validators in the overlay, degraded states, the audit trail. User testing: the round 3 kit and the scoring script. Real scenarios: slow, paused and offline states.
