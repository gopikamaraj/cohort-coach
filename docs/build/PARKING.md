# Parking lot

New ideas that are not in `BUILD_PROMPTS.md`. Nothing here is built until every P0 phase is done.

| Date | Idea | Why it came up | Who |
| --- | --- | --- | --- |
| 2026-10-16 | Bind eval results to a commit hash so a stale result is detectable after engine changes | P02 integrity review (note 5) | Gopi |
| 2026-10-16 | Salt `input_hash` with a server secret, or keep it off public endpoints | P03 privacy review | Gopi |
| 2026-10-16 | Disable `/api/judge/audit` (or limit to judge rows) in production for real teachers | P03 privacy review | Gopi |
| 2026-10-17 | Derive the `judge` flag server-side (signed deep link or env), not from the request body; add a per-IP rate limit to `/api/practice` before the public staging URL | P04 privacy review | Gopi |
| 2026-10-17 | Full 200-turn live fidelity run, the 150-line labeller eval and the full 50-prompt red team (P13); re-measure text-turn latency after the voice check-then-release (P07) and the server move (P15) | P04 judge review | Gopi, Shivani |
| 2026-10-17 | Show one turn's `layers` in the judge-mode overlay with a screenshot for the deck (P06) | P04 judge review | Gopi |
| 2026-10-17 | Route `/api` to the API in staging so the judge-mode AI map and audit links work from a static PWA host (P15); add deep links for judge steps 1 and 5 once the Practice Class screen exists (P06) | P05 judge review | Gopi |
| 2026-10-17 | Measure Slow 3G and a real low-end phone; add a Playwright test that the send queue survives a restart (P14) | P05 judge review | Gopi |
| 2026-10-17 | When a flag sender is built keep the payload `{card, term}` with no free text; empty the photo outbox after each photo is read (P08) | P05 privacy review | Gopi |
