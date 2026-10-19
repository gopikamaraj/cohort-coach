# Migration: kit v1 to kit v3 (19 Oct 2026)

**Status:** plan written; NOW items MIG-T01 to MIG-T03 below; reviews and the closing summary are appended at the end.

## 1. What was found (step 1)

The "copy over the repo" was partial: only `CLAUDE.md` was overwritten in place. The other v3 files sat untracked at the repo root (`BUILD_PROMPTS.md`, `DECISIONS.md`, `PROGRESS.template.md`, `evidence-digest.md`, three agent files) and the rest of the kit (STARTER_PROMPT, skills, templates, design docs) was not copied. The complete v3 kit is inside `fln_src/files (2).zip` (`cohort-coach-claude-kit-v3.zip`); I verified the root files are byte-identical to it and used the zip as V3. V1 is `ac4a940` (also `cohort-coach-claude-kit.zip`). BUILD is `HEAD` (`f416be8`): nothing in the kit files was uncommitted except the overwritten `CLAUDE.md`, so BUILD for `CLAUDE.md` is also `HEAD`. A snapshot of the v3 files given is in `/tmp/kit-v3-snapshot/`.

| File | BUILD differs from V1? | V1 differs from V3? | Result |
| --- | --- | --- | --- |
| `CLAUDE.md` | yes (one line: Speech, no finguru) | yes | merged (3-way) |
| `docs/build/DECISIONS.md` | yes (OD-1, OD-2 text; 15 build entries) | yes | merged (3-way) |
| `docs/build/BUILD_PROMPTS.md` | no | yes | v3 taken as is |
| `docs/build/templates/PROGRESS.template.md` | no | yes | v3 taken as is |
| `.claude/agents/{integrity-auditor,judge-reviewer,privacy-guardian}.md` | no | yes | v3 taken as is |
| `docs/design/evidence-digest.md` | n/a (new) | n/a | added from v3 |
| `STARTER_PROMPT.md`, `REPORT` and `TASKS` templates, three skills, `cohort-coach-design.md`, `pilot-test-pack.md`, `pilot_forms.golden.json` | no | no | unchanged |

## 2. Build-time changes re-applied (step 2)

- **`CLAUDE.md`:** the Speech line ("called directly from our own server… No finguru voice server; `services/speech/` is built fresh"). One conflict: v3 rewrote the next bullet ("Messaging" became "Flows and channels"). Resolved by keeping the build's Speech line and v3's new "Flows and channels" bullet.
- **`DECISIONS.md`:** OD-1 ("MIT (applied in P00)") and OD-2 (voice decided no) merged cleanly. One conflict at the top of "Settled decisions": v3 added four 19 Oct entries, the build added 15 entries from 16 and 17 Oct. Resolved by keeping both, newest first (v3's four, then the build's); no entry dropped (30 entries: 11 from v1, 15 from the build, 4 new in v3).
- **Lost and unrecoverable:** nothing. The only overwritten tracked file was `CLAUDE.md` and its build change was one line, recovered. Everything else the build wrote is in git and untouched.
- **`PROGRESS.md`:** new phase titles (P05, P08, P10, P12); P04 steps 11 and 12 marked open and pointed to P06; the bot token is now a P05 blocker in "Waiting on people"; OD-11 to OD-14 added; a note that P05 is reopened for the v3 rewrite.
- Commit: `ad5fa7c docs: adopt kit v3, re-apply build-time changes`.

## 3. Decisions you must confirm

1. **Supersession.** v3's 19 Oct entries (two channels, one back end; Telegram-first) supersede the build's 17 Oct "P05 PWA decisions" where they conflict: on-device check entry with `checks`, `profiles` and `syncQueue` in Dexie, and a phone-made class id. I kept both and added a reconciling entry (MIG-T03) saying v3 wins and the v1 code is the interim typed fallback until P05 and P08 replace it. Confirm.
2. **P05 status.** I set P05 back to ⬜ (the v1 work is the base, the v3 rewrite is new work). Confirm, or say to keep it ✅ and open a new phase instead.
3. **Stale v1 copies outside the repo.** `fln_src/CLAUDE.md`, `fln_src/BUILD_PROMPTS.md` and `fln_src/STARTER_PROMPT.md` (dated 16 Oct) are still v1, and the parent `CLAUDE.md` is loaded into every session before the repo's one (it still says "reuse the finguru voice server"). I did not touch files outside the repo. Replace them with the v3 files or delete them.

## 4. The audit (step 3) and plan (step 4)

NOW = breaks a non-negotiable, makes a test or the docs lie, or blocks P05. Everything else folds into the phase that owns it; each folded item is appended to that phase's file in `docs/build/tasks/`.

| # | Item | v3 source | Current state | Action | When | Test that proves it |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Server stores class counts only, no per-child rows | CLAUDE.md §4.2 | Compliant: `services/api/db.py` tables are class counts, AI audit (metadata), speech log (metadata), review, flags, consents; `ProfileIn` is `extra=forbid` (`services/api/profiles.py:37`) | none | done | `tests/api/test_profiles.py`, `tests/data` (no per-child output) |
| 2 | Dexie holds per-child answers (`checks`) plus `profiles`, `syncQueue`; v3 limits Dexie to transcripts and the photo outbox | §6 Client, P05 step 4 | `apps/pwa/src/lib/db.ts:84-92` stores all of them; on-device only, never sent | Replace with flow-engine check (photos, `number_grid` typed fallback); drop `checks`/`profiles`/`syncQueue` after the photo flow lands; keep `transcripts`, `outbox`, `settings` | P05 then P08 | Vitest: schema has only the allowed stores; payload contract test |
| 3 | Check photos via bot or PWA; per-sheet reads in memory, 30-min TTL; photo deletion in Telegram and PWA outbox | §4.2, P08 steps 2–5 | Absent (`outbox` store exists, unused) | Build in P08 | P08 | golden transcript; temp-file and log assertions; TTL test |
| 4 | `services/api/flows/` flow engine; thin adapters; WhatsApp stub | §4.14, §6, P05 | `flows/` absent; `channels/{telegram,whatsapp}/` are empty packages | Build in P05 | P05 | engine transitions; adapter contract tests |
| 5 | Import rule: channels and PWA import nothing from `engine/` or `ai/` | rule 14, P05 tests | Nothing to violate yet (channels are empty); no rule exists | Add test with the flow engine | P05 | the import-rule test |
| 6 | Copy in `strings/{en,hi,ta}.json` shared with the bot | §6, P05 step 7 | Copy lives in `apps/pwa/src/i18n/` | Move to `strings/` when the bot needs it; keep the CSV export | P05 | `i18n.test.ts` key completeness reads `strings/` |
| 7 | One pseudonymous teacher id across channels, linking code, one consent, "Delete my data" | P05 step 3 | `consents` table only; no teacher id | Build in P05 | P05 | cross-channel linking and delete tests |
| 8 | Registry ready for 9 calls; call 9 "arrives in P10" on the AI map | §7, P06 step 3 | Registry and `AiMap.tsx` list 8; P03 acceptance already says "8 design calls (call 9 joins in P10)" | Add a planned-call row (P06), register call 9 with its prompt in P10 | P06 / P10 | `AiMap` shows a 9th row; registry test lists 9 in P10 |
| 9 | `MODEL_POINTER` in `.env.example` and `ai/config.py` | §7 row 9, rule 9 (`.env.example` lists every key) | Absent | Add | **NOW** | MIG-T02 |
| 10 | Rule 13: say simulated practice is a hypothesis the pilot tests | §4.13 | README and `docs/practice-class.md` do not say it (grep: no "hypothesis") | Add | **NOW** | MIG-T01 |
| 11 | Rules 11, 12 wording (no "listened" or "completion = adoption") | §4.11–12 | No violation found: "proven" appears only as the defined mentor tier; "listened" in `docs/speech.md` is about humans reviewing pronunciations | none | done | grep recorded in this report; `tests/test_kit_v3.py` guards it (MIG-T01) |
| 12 | No problem claim without a DOC + page | §3 | README has no problem claims; the Practice Class text claims nothing about the school system | none now; check again at P16 | P16 | integrity-auditor item 9 |
| 13 | DECISIONS and docs stay true: v1 P05 decisions vs v3; P07 key rejected entry now stale (key works, latency measured) | §2 | Entries say "key rejected"; P05 entries describe on-device check as final | Add reconciling entries; banner in `docs/offline.md` and `docs/architecture.md` | **NOW** | MIG-T03 |
| 14 | `content/model_runs/`, `engine/model_run.py`, `scripts/render_model_run.py`, scenario flag `mixed_level` (default false) | P04 steps 11–12 | Absent; scenario schema has no `mixed_level` | Build at the start of P06 (P04 is closed) | P06 | determinism by seed; engine-number match; schema default |
| 15 | P06: "Hear it done well" button, `link` entry for the Practice Class, `/r/<token>` | P06 steps 1–2 | Not built | Fold into P06 and P05 (`/api/practice/link`) | P06 | Playwright |
| 16 | P07: 5 voice sessions on Slow 3G, bytes per session | P07 step 8 | Not measured | Run with the next live session | P07 follow-up | `docs/evidence/data_budget.json` |
| 17 | P09 step 10: publish the SUB-SFL model run (review, voice, manifest) | P09 | Not built | Fold into P09 | P09 | pipeline test; size ≤ ~0.35 MB |
| 18 | P10: T4/T6 flows, lessons as `media`, reflections, call 9, time budget | P10 | Not built | Fold into P10 | P10 | golden transcripts; call 9 validators |
| 19 | P12: roles, weekly batch, funnel with source labels, visit brief | P12 | Not built | Fold into P12 | P12 | funnel and visit-brief tests |
| 20 | P13: eval 10 (reflection pointer); model runs join eval 2; cost script gains reflections; time-budget evidence | P13 | `tasks.py` has no slot for eval 10 | Fold into P13 | P13 | runner exists; eval 2 covers model runs |
| 21 | P14: offline tests per matrix row rewritten for both channels | P14 | Not built | Fold into P14 | P14 | per-row tests |
| 22 | P16: five evidence figures, the hypothesis slide, problem-claims check | P16 | Not built | Fold into P16 | P16 | integrity-auditor items 9–11 |
| 23 | `docs/privacy.md` (photo and read lifecycle per channel) | P08 docs | Absent (P06 report mentions it) | Write in P08 | P08 | doc exists; privacy-guardian |
| 24 | Dependencies for P05: `python-telegram-bot` ≥ 21, an import-rule tool | P05 step 2 | Not installed | Add in P05 | P05 | CI |
| 25 | Telegram bot token and handle | P05 human input | `TELEGRAM_BOT_TOKEN=` is in `.env.example`, no value | **Human: Gopi** | before P05 | n/a |
| 26 | Stale v1 files outside the repo (see §3.3) | n/a | present | **Human: Gopi** | now | n/a |

### Hours and calendar

- **NOW work:** about 2 hours (three small tasks, all documentation, config and one guard test; no phase work).
- **Calendar risk: high.** v3's P05 is the flow engine, three adapters, identity and consent, generic PWA step components, the outbox and the golden-transcript harness, on top of an existing v1 PWA that must be partly replaced. I estimate 14 to 18 hours of work against one day (Tue 20 Oct). Before P06 can finish there are also the P04 carry-overs (model-run renderer, `mixed_level`) and the P06 follow-ups (model-run button, 9-call map): another 4 to 6 hours. NOW plus P05 will not fit by end of Tue 20 Oct; realistic finish for P05 is Wed 21 evening, which moves P06 follow-ups, staging (already blocked on accounts) and P08 by about a day. Mitigations from the cut list that cost least: cut-list items 8 (PWA web push and PWA voice reflections), 6 (WhatsApp stub; but P05 says the stub passes the contract, so keep the stub minimal), and 2 (mixed-level persona, so P04 step 12 can be skipped). The bot token is the only thing that can block P05's start.

## 5. NOW tasks (step 5)

(commits and results are added below as each lands)
