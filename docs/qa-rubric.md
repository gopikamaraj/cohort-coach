# Browser QA rubric

How every page of the web app is judged in a real browser. Results are generated into [docs/evidence/browser_qa.md](evidence/browser_qa.md); nothing is scored by hand.

## How it is run

1. Build the web app and start the API in recorded and stub mode (no paid calls): see `apps/pwa/playwright.config.ts` for the settings.
2. `node apps/pwa/qa/crawl.mjs docs/evidence/browser_qa` opens every route in Chromium in English, Hindi and Tamil, at a 360 px phone width and a 1280 px desktop width (132 page views), and writes `report.json`.
3. `npx playwright test --reporter=list > docs/evidence/browser_qa/e2e_list.txt` runs the feature tests (taps, forms, offline, voice, review, cohort).
4. `python scripts/browser_qa_report.py` scores each route.

## The five criteria (0 to 2 each, 10 in all)

| Criterion | 2 | 1 | 0 |
| --- | --- | --- | --- |
| Loads clean | No blank page, console error, failed API call or "undefined" in all 6 views | 1 view fails | 2 or more fail |
| Languages | No raw string key or blank page in Hindi or Tamil | 1 view fails | 2 or more fail |
| Layout and touch | No horizontal scroll at either width; every tap target at least 40 px high on the phone (the design asks for 44) | 1 view fails | 2 or more fail |
| Browser feature test | At least 2 passing feature tests drive the page | 1 test | None |
| Rules | No percentage, "percent" or its Hindi or Tamil word on a teacher screen | 1 view fails | 2 or more fail |

Bands: Pass 9 to 10, Partial 6 to 8, Gap 5 or less.

## What this does not cover

- A real low-end phone and Slow 3G (the checklist item Gate 2): the crawl uses Chromium with a phone viewport.
- Telegram: the same flows are covered by the golden-transcript tests through each adapter, not in a browser.
- Live AI and live speech: the run uses recorded fixtures and stub speech, so it tests the screens, not the models.
- Whether a page is easy to understand. That needs the user-testing rounds (`docs/feedback-log.md`).
- The crawl opens each page in its first state, as an officer, so a page that needs a longer journey to reach its main content is judged by its feature tests, not by the crawl.
