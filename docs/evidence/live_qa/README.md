# Live site browser QA (28 Oct 2026)

Run against https://cohort-coach-pwa-1097171252131.asia-south1.run.app (judge API and pilot API behind it). Real Chromium, live Claude and Sarvam. Files here are raw tool output; nothing is typed by hand.

| File | What it is |
| --- | --- |
| `live_walk.txt` | `apps/pwa/qa/live-walk.mjs`: 31 steps through every page and main feature, phone size |
| `crawl.txt` | `apps/pwa/qa/crawl.mjs` with `QA_BASE`: 22 routes x 3 languages x phone and desktop = 132 page views |
| `spec_run_against_live.txt` | the 106 local feature specs (`playwright.live.config.ts`) pointed at the live site: 75 passed, 31 failed |

Reading the spec run: those specs were written for a local server in recorded mode that is not in judge mode. On the live judge server the top bar has role and language selectors the specs do not expect, Practice replies take about 4 to 5 seconds (the specs wait 5), and Admin is closed (no `ADMIN_KEY`). So the 31 failures are mostly mismatches between spec and deployment, not proven app faults; the walk and the crawl are the evidence for the live site. Not covered: real phone, Slow 3G, Telegram, Sarvam voice in the browser (fake microphone only).
