# Offline, low data, cheap phones (v1, after P05)

> **Kit v3 (19 Oct):** this page describes the v1 build, where the check is entered on the phone and only counts sync. In v3 the check arrives as photos through the bot or the PWA and the flows run on one back end; this page is rewritten in P05 and P14. See `docs/build/DECISIONS.md` (2026-10-19 · Kit v3 adopted) and `docs/build/reports/MIGRATION-v1-v3.md`.

Only the Practice Class needs a live connection. Everything else works offline or queues until a signal returns. This page is the matrix, with how each row is verified. Rows for features built in later phases are marked "later" and are filled in as they land.

**Target phone:** an Android Go-class phone with 2 GB of RAM running Chrome. **Install:** a PWA from the browser, no app store. **First load:** under 1 MB of compressed JavaScript; the measured figure is in `docs/evidence/bundle_size.json`. Fonts are the phone's system fonts and there are no images, only SVG icons.

## The trade-off, said plainly

Rehearsing with simulated children is the most useful feature and the only one that needs a live connection. It falls back to text on a weak signal, and (P14) to practice cards with scripted branches when offline. The check, the diagnosis, the error cards and, later, the lessons all work with no signal.

## Matrix

| Feature | Offline | Needs a connection for | Falls back to | Verified by |
| --- | --- | --- | --- | --- |
| App shell and all screens | Works after the first load: the service worker precaches every file | The first load | n/a | `apps/pwa/e2e/app.spec.ts` "works offline after the first load" and "is installable" |
| Check entry (T2) and diagnosis | Works fully; every key is saved on the phone | Sending counts | Counts wait in a queue | `e2e/app.spec.ts` "a teacher enters a 10-child check", "autosaved … after a reload"; `src/lib/flow.test.ts` |
| Error cards (T3) | Works fully; built on the phone from the saved result | Nothing | n/a | `e2e/app.spec.ts` "works offline after the first load" |
| Sending class counts | Queued in IndexedDB, sent when a signal returns and on every app open | The send itself (about 2 KB per class) | A queue that survives restarts | `src/lib/flow.test.ts` (queue, flush, retry, drop-on-4xx); `e2e/app.spec.ts` "Simulate offline …" |
| Simulate offline (judges) | Forces the offline behaviour in the demo | n/a | n/a | `e2e/app.spec.ts` "Simulate offline stops sending …" |
| Languages (en, hi, ta) | Switch at runtime with no connection | Nothing | English for any missing string | `src/i18n/i18n.test.ts`; `e2e/app.spec.ts` "languages switch at runtime" |
| Voice lessons, model-lesson script | later (P09, P10) | First download | Text script | later |
| Answer-sheet photos | later (P08): taken offline, queued | Reading | Manual keypad entry (built) | later |
| Practice Class | Not available offline: the screen says so and sends nothing; a slow or failed model call falls back to a template line with a notice; when the day's budget is spent a recorded sample rehearsal can be watched | Every turn | Template line, sample rehearsal; practice cards (P14) | `apps/pwa/e2e/practice.spec.ts` "offline, practice says so", "a class's own counts … a slow reply is explained", "paused … sample" |
| Voice in the Practice Class (P07) | Not available offline (it is part of the Practice Class) | Every turn: recording up, reply audio down | Typing, switched on by itself after 2 voice failures or on a 2g link; the server skips speech for 30 s after 3 failures | `apps/pwa/e2e/voice.spec.ts`; `tests/speech/test_voice_turn.py`; live latency pending a working key, see `docs/speech.md` |
| Reflection replies, mentor method capture | later (P10, P11) | Sending | Typed reply | later |

## Flags

A teacher's "this is wrong" tap on an error card is kept in the phone's queue for now (the card says so). The server has no endpoint that stores flags yet; it comes with the review queue (P09). The payload stays `{card, term}` with no free text.

## What stays on the phone

Per-child answers (`checks`), the class result (`profiles`), the send queue, Practice Class transcripts (P06) and queued photos (P08) live in IndexedDB on the phone (`apps/pwa/src/lib/db.ts`). The server receives class-level counts only; its schema rejects any other field (`services/api/profiles.py`, `tests/api/test_profiles.py`), and a Vitest contract test and a Playwright network assertion check the same from the client side.

## Data per use (targets and what is measured)

| What | Target | Measured |
| --- | --- | --- |
| Initial JavaScript, compressed | under 1 MB | `docs/evidence/bundle_size.json` |
| Check-entry sync | about 2 KB per class | the payload is asserted under 2 KB by `apps/pwa/src/lib/flow.test.ts`; not yet measured over a real request |
| Voice lesson, Practice Class, photos | see `CLAUDE.md` section 9 | later phases |

Throttled mobile Lighthouse figures (emulated phone, simulated slow 4G, CPU slowed 4×) are in `docs/evidence/lighthouse_mobile.json`; they are one run on one machine, so read them as directional. Screenshots at 360 px in the three languages are in `docs/evidence/screenshots/`. A run on a real low-end phone is still to be done (P14).

## Screens added 2026-10-20

| Screen | Offline | Needs a connection for |
| --- | --- | --- |
| What I entered | Works fully (reads this phone) | Nothing |
| My programme | Shows the steps known on this phone; cohort and lessons need the server | Cohort and lesson status |
| Class observation | Saved on the phone, sent when online | The send |
