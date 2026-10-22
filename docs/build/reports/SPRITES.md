# Sprite system (P17) report

Date: 2026-10-22. Spec: `docs/design/sprite-system.md`. Decisions: `DECISIONS.md` (22 Oct, Sprite system).

## Built

| Part | Where | Evidence |
| --- | --- | --- |
| Grammar (shape and attribute whitelist, slots only, budgets, no text) | `services/api/sprites/grammar.py` | `tests/sprites/test_grammar.py` |
| Ten layouts, exact counts | `services/api/sprites/layouts.py` | `tests/sprites/test_layouts.py` (counts 0 to 100, bundles of ten, mat 0 to 99, cross_out n of N) |
| Avatars, seven expressions, state-to-expression table | `avatar.py`, `expression.py` | `tests/sprites/test_avatar.py`, `tests/practice/test_faces.py` |
| Packs and the two-key lifecycle | `packs.py`, `content/sprites/packs/` | `test_packs.py`; second pack `fractions-demo` is JSON only (`test_extensibility.py`) |
| TypeScript renderer, byte-identical | `apps/pwa/src/sprites/` | `golden.test.ts`: 114 cases (SHA-256 and length) against `tests/fixtures/sprite_golden.json`, written by Python |
| Call 11 (offline author) and its gates | `ai/calls/c11_sprite_author.py`, `services/api/sprite_gates.py` | `tests/sprites/test_authoring.py` (every gate has a failing case; fake client, no paid call) |
| PNG via `resvg-py` and scene steps in every channel | `png.py`, `services/api/sprite_media.py`, Telegram `sendPhoto` | `tests/sprites/test_channels.py` |
| Practice Class faces, tray, judge sprite-spec panel | `services/practice/faces.py`, `apps/pwa/src/components/practice.tsx` | `tests/practice/test_faces.py`; Playwright full run |
| Contact sheet | `scripts/sprite_contact_sheet.py` | `docs/evidence/sprites/contact-sheet.png` and `.json`: 0 validator failures |

## Results (commands run 22 Oct)

- `pytest tests`: 1436 passed before the final accessory fix; sprite and practice subsets re-run after it.
- `npx vitest run`: 335 passed; sprite parity 115 passed after the golden fixture was regenerated.
- `tsc --noEmit` and `eslint src`: clean. Bundle: one JS file, 188 KB gzipped (budget under 1 MB).
- Playwright (production build, recorded AI mode): the full suite listed all specs ok on the second run. The first run failed once on "layers toggle absent for teachers" in `practice.spec.ts:115` and passed on the second; not investigated (the check depends on the judge-deployment flag, which commit 49138c0 made follow the server).
- Renderer hash `5a377b0f…690c` (20 files) recorded in fa50ee3, unchanged in cf99a84 and after.

## Review findings and what was done

- Privacy: first-seating response leaks nothing (checked). Removed the `glasses` and `ribbon` accessories (possible disability and gender markers); golden fixture regenerated, hash unchanged. Open: confirm skin-tone set with Seema. `has_error` per child still comes with each turn's meter (existing design, simulated).
- Integrity: hash claim, golden parity and evidence files hold. Fixed: hash scope stated in DECISIONS; this report written.
- Judge review: PASS WITH FIXES. Blocking: work was uncommitted (committed with this report). Open, not fixed: `docs/roadmap.md` does not exist yet (P16 owns it; add a sprites section then: pack approval, live call 11 run, hi/ta string review, WhatsApp images); `counter` and `marble` look alike on the contact sheet and `ball` and `mango` are close at small sizes (the outline and shape carry meaning, but `marble` should be redrawn); the ten-frame tile at count 1 is faint; no measured KB per scene on Slow 3G, no screenshot of faces and tray, no link yet to a Challenge 3 gap (G2) or a feedback-log entry. The "nine items" in DECISIONS is the pack's count; the contact sheet's ten includes `chapati` from the draft pack.

## Not done or not verified

- Coach approval and officer enablement of `place-value-add-sub` (TODO-HUMAN Seema): it is enabled for the build and demo only. Hindi and Tamil sprite strings are drafts.
- No live run of call 11 (paid), so no eval row; `content/sprites/drafts/` is not created until one runs. Its alt-text rule bans digits; number words are only prompted against.
- Real low-end phone and Slow 3G not tested for the new sprites. Telegram `sendPhoto` is tested against a fake HTTP post, not the real Bot API.
- Watch recorded runs were not re-recorded (needs paid calls); their faces are derived from recorded facts, with engagement assumed neutral.
