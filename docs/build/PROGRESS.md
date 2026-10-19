# Build progress

<!-- HANDOFF: when the loop stops, it writes this block. Delete it once acted on. -->
> **Handoff** — P07 built and run live once; voice latency over target
> - Where we are: P07 🟡 (voice turn, hold-to-speak, text fallback, stub speech, limits, scripts). The new Sarvam key works: 36 child-voice clips synthesised and 24 live voice turns timed, median 7515 ms against the 5 s target (not met; plan in `docs/speech.md`). P06 staging is still not deployed.
> - Needed from people: 1. Run `python scripts/check_voices.py --out <folder>` and listen to the 36 clips: five distinct children? (Gopi, Shivani). 2. Listen for five distinct children in hi, ta, en; Hindi and Tamil review of the new strings (Shivani, Seema, Gopi). 3. Hosting accounts for staging, `docs/deploy.md` (Gopi). 4. Round 3 with Seema.
> - **Kit v3 adopted 2026-10-19 (see `docs/build/reports/MIGRATION-v1-v3.md`).** P05 is now the flow engine and channel adapters and needs the Telegram bot token before it starts (Gopi). The next phase is decided after the migration is reviewed; do not run `/next-phase` until Gopi says go.

**Today:** 2026-10-19 · **Days to submission (31 Oct):** 12 · **Budget spent:** USD 0.52 of 350 (judging reserve 150 untouched)

## Phases

Status: ⬜ not started · 🔄 in progress · ✅ done · 🟡 done with non-blocking gaps · ❌ failed · ⛔ blocked · ✂️ cut

| ID | Phase | Priority | Target | Status | Started (commit) | Finished | Report | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | Bootstrap, inventory, decisions | P0 | Fri 16 Oct | ✅ | 2026-10-16 14:46 (`ac4a940`) | 2026-10-16 | [report](reports/P00-bootstrap.md) | CI green on `83e571b` (run 38881893876) |
| P01 | Engine core | P0 | Fri 16 – Sat 17 | ✅ | 2026-10-16 15:30 (`f92f846`) | 2026-10-16 | [report](reports/P01-engine-core.md) | CI for this phase after push; Seema to confirm key variants |
| P02 | Simulated block, grouping, mentors, statistics | P0 | Sat 17 | ✅ | 2026-10-16 20:45 (`a0d858f`) | 2026-10-16 | [report](reports/P02-simulated-block-statistics.md) | CI for this phase after push; demo cohorts small by design |
| P03 | AI platform and guardrails core | P0 | Sun 18 | ✅ | 2026-10-16 (`9bfc51c`) | 2026-10-17 | [report](reports/P03-ai-platform-guardrails.md) | Live red team on 12 seeds passed; cache hits confirmed |
| P04 | Practice Class engine + calls 1–3 (text) | P0 | Mon 19 | 🟡 | 2026-10-17 (`6b18369`) | 2026-10-17 | [report](reports/P04-practice-class-engine.md) | Gate 1 end-to-end passed; text-turn latency over 3 s (plan in report). **v3 acceptance is open: steps 11 (model-run renderer) and 12 (`mixed_level` flag) are not built; do them at the start of P06 (tasks in `tasks/P06.md`)** |
| P05 | Flow engine, channel adapters, PWA shell, judge mode | P0 | Tue 20 | ⬜ reopened | 2026-10-17 (`6306eb7`) | 2026-10-17 | [report](reports/P05-pwa-shell-check-cards.md) | v1 build kept as the base; v3 rewrite pending (tasks: `tasks/P05.md`, v3 carry-over). Blocked on the bot token. v1: Installable, offline T1–T3, 3 languages, bundle 112 kB |
| P06 | Practice Class UI, overlay, staging | P0 | Wed 21 | 🟡 | 2026-10-17 (`0e57872`) | 2026-10-17 | [report](reports/P06-practice-class-ui.md) | Staging blocked on hosting accounts; v3 follow-ups open (model-run button, 9-call map) |
| P07 | Voice | P0 | Thu 22 | 🟡 | 2026-10-17 (`874d069`) | 2026-10-17 | [report](reports/P07-voice.md) | Built; run live once (24 turns, median 7515 ms, over the 5 s target; plan documented). Open: voice latency fix, bytes per session on Slow 3G (v3), listening check |
| P08 | Answer-sheet capture (both channels) and import | P0/P1 | Fri 23 | ⬜ | | | | |
| P09 | Content pipeline | P0 | Sat 24 | ⬜ | | | | |
| P10 | Teacher flows on both channels | P0 | Sun 25 | ⬜ | | | | |
| P11 | Mentor loop | P1 | Sun 25 | ⬜ | | | | |
| P12 | Officer views, funnel, roles, visit brief | P0 | Mon 26 | ⬜ | | | | Gate 2 |
| P13 | Evals, red team, cost, latency | P0 | Tue 27 | ⬜ | | | | |
| P14 | Real-scenario hardening | P0 | Tue 27 | ⬜ | | | | |
| P15 | Production deploy and freeze | P0 | Wed 28 | ⬜ | | | | Freeze |
| P16 | Submission pack | P0 | Thu 29 – Fri 30 | ⬜ | | | | |

## Gates

| Gate | Due | Status | Evidence |
| --- | --- | --- | --- |
| Gate 1: SUB-SFL text rehearsal end to end | Mon 19 Oct | ✅ | recorded and live rehearsal; `docs/evidence/practice_session_live.json`, `tests/practice/test_recorded_session.py` |
| Staging live for test round 3 | Wed 21 Oct | ⛔ BLOCKED: hosting accounts and secrets (Gopi); round 3 can use a laptop plus hotspot or `python tasks.py dev` | recipe in `docs/deploy.md` |
| Gate 2: all storyboard screens on a low-end phone | Mon 26 Oct | ⬜ | |
| Freeze: production smoke-tested | Wed 28 Oct | ⬜ | |
| Submitted | Sat 31 Oct | ⬜ | |

## Waiting on people (TODO-HUMAN)

| Owner | Item | Needed by phase | Placeholder in place? | File |
| --- | --- | --- | --- | --- |
| Gopi | **Telegram bot token (BotFather) in `.env` as `TELEGRAM_BOT_TOKEN`: blocks P05 (v3 moved the bot into P05)**; reuse paths optional | P05 | no | `.env.example` |
| Shivani, Gopi | Review hi/ta/Hinglish profanity lists; full 50 red-team prompts | P13 | yes (12 seeds) | content/safety/, evals/sets/redteam.yaml |
| Seema, Gopi | Native review of hi/ta number words, jargon, error names, badge and explanation wording | P09 | yes (drafts) | content/lang/, ai/guard/ |
| Shivani | Review Hindi UI strings (`python scripts/i18n.py export`) | P06 | yes (draft) | apps/pwa/src/i18n/hi.json |
| Gopi | Review Tamil UI strings; confirm P05 DECISIONS | P06 | yes (draft) | apps/pwa/src/i18n/ta.json |
| Seema | Review P04 move lists, rubrics, scenario values, personas and hi/ta templates | P06 | yes (drafts) | content/ |
| Shivani | 150 labelled lines for the labeller eval; realism ratings; 50 red-team prompts | P13 | no | evals/sets/ |
| Gopi | Make repo public before submission (`gh repo edit --visibility public`) | P16 | n/a | — |
| Seema | Review fictional teacher names | P05 | yes (draft list) | content/personas/teachers_simulated.yaml |
| Seema | Confirm extra heard-and-reversed variants (3064, 300604) and NCERT match of the 20 items | P04 | yes | docs/engine.md |

## Open decisions from kit v3 (defaults apply; see DECISIONS.md)

| ID | Question | Default | Needed by | Owner |
| --- | --- | --- | --- | --- |
| OD-11 | How judges see the teacher flow | Real flows in the PWA's judge mode on simulated data, and the same flows in Telegram with `/start judge` | P05 | Gopi |
| OD-12 | Time caps | Teacher at most 20 min a week, mentor 30, reviewer 15; revisit with round 4 data | P10 | Seema |
| OD-13 | Who holds the reviewer and officer roles in the pilot | Seema holds both; a DIET faculty member or head teacher takes one if they agree | P12 | Seema |
| OD-14 | Pilot roll numbers | Unique roll number from the register on each sheet; Seema confirms the register is stable between tests | Pre-test day | Seema |

## Environments (no secrets here)

| Environment | URL | Last deploy | Notes |
| --- | --- | --- | --- |
| Staging | | | |
| Production | | | |
| Telegram bot | @… | | |

## Cuts taken

| Date | Cut | Why | Moved to |
| --- | --- | --- | --- |
