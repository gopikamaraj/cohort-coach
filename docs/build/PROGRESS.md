# Build progress

<!-- HANDOFF: when the loop stops, it writes this block. Delete it once acted on. -->
> **Handoff** — P07 built and run live once; voice latency over target
> - Where we are: P07 🟡 (voice turn, hold-to-speak, text fallback, stub speech, limits, scripts). The new Sarvam key works: 36 child-voice clips synthesised and 24 live voice turns timed, median 7515 ms against the 5 s target (not met; plan in `docs/speech.md`). P06 staging is still not deployed.
> - Needed from people: 1. Run `python scripts/check_voices.py --out <folder>` and listen to the 36 clips: five distinct children? (Gopi, Shivani). 2. Listen for five distinct children in hi, ta, en; Hindi and Tamil review of the new strings (Shivani, Seema, Gopi). 3. Hosting accounts for staging, `docs/deploy.md` (Gopi). 4. Round 3 with Seema.
> - **Kit v3 adopted 2026-10-19 (see `docs/build/reports/MIGRATION-v1-v3.md`).** P05 is now the flow engine and channel adapters and needs the Telegram bot token before it starts (Gopi). The next phase is decided after the migration is reviewed; do not run `/next-phase` until Gopi says go.

**Today:** 2026-10-22 · **Days to submission (31 Oct):** 9 · **Budget spent:** USD 0.52 of 350 (judging reserve 150 untouched)

## Phases

Status: ⬜ not started · 🔄 in progress · ✅ done · 🟡 done with non-blocking gaps · ❌ failed · ⛔ blocked · ✂️ cut

| ID | Phase | Priority | Target | Status | Started (commit) | Finished | Report | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | Bootstrap, inventory, decisions | P0 | Fri 16 Oct | ✅ | 2026-10-16 14:46 (`ac4a940`) | 2026-10-16 | [report](reports/P00-bootstrap.md) | CI green on `83e571b` (run 38881893876) |
| P01 | Engine core | P0 | Fri 16 – Sat 17 | ✅ | 2026-10-16 15:30 (`f92f846`) | 2026-10-16 | [report](reports/P01-engine-core.md) | CI for this phase after push; Seema to confirm key variants |
| P02 | Simulated block, grouping, mentors, statistics | P0 | Sat 17 | ✅ | 2026-10-16 20:45 (`a0d858f`) | 2026-10-16 | [report](reports/P02-simulated-block-statistics.md) | CI for this phase after push; demo cohorts small by design |
| P03 | AI platform and guardrails core | P0 | Sun 18 | ✅ | 2026-10-16 (`9bfc51c`) | 2026-10-17 | [report](reports/P03-ai-platform-guardrails.md) | Live red team on 12 seeds passed; cache hits confirmed |
| P04 | Practice Class engine + calls 1–3 (text) | P0 | Mon 19 | 🟡 | 2026-10-17 (`6b18369`) | 2026-10-17 | [report](reports/P04-practice-class-engine.md) | Gate 1 end-to-end passed; text-turn latency over 3 s (plan in report). **v3 acceptance is open: steps 11 (model-run renderer) and 12 (`mixed_level` flag) are not built; do them at the start of P06 (tasks in `tasks/P06.md`)** |
| P05 | Flow engine, channel adapters, PWA shell, judge mode | P0 | Tue 20 | 🟡 | 2026-10-17 (`6306eb7`) | 2026-10-20 (`84cdad6`) | [report](reports/P05-flow-engine-adapters.md) | v3 backend built: flow engine, onboarding and T1, web/Telegram/WhatsApp-stub adapters, golden transcripts. Open: real-phone check (Gopi), PWA photo/voice step components (P08), Dexie reduction, QR code, server-side judge API. v1: Installable, offline T1–T3, 3 languages, bundle 112 kB |
| P06 | Practice Class UI, overlay, staging | P0 | Wed 21 | 🟡 | 2026-10-17 (`0e57872`) | 2026-10-17 | [report](reports/P06-practice-class-ui.md) | Staging blocked on hosting accounts; v3 follow-ups open (model-run button, 9-call map) |
| P07 | Voice | P0 | Thu 22 | 🟡 | 2026-10-17 (`874d069`) | 2026-10-17 | [report](reports/P07-voice.md) | Built; run live once (24 turns, median 7515 ms, over the 5 s target; plan documented). Open: voice latency fix, bytes per session on Slow 3G (v3), listening check |
| P08 | Answer-sheet capture (both channels), stages, roles shell, Practice Class demo modes, import | P0/P1 | Fri 23 | 🟡 | 2026-10-22 (`a59ade4`) | | [addendum report](reports/P08-addendum-v3.1.md) | Addendum v3.1 items built (roles shell, call 10, Watch, hints, break-it, strategies, stages, sample sheets, tour shell). **Not started: P08's own capture scope** (check flow on both channels, importers, eval 9) |
| P09 | Content pipeline, versions and the two keys, strategies | P0 | Sat 24 | ⬜ | | | | |
| P10 | Teacher flows on both channels | P0 | Sun 25 | ⬜ | | | | |
| P11 | Cohort space, mentor pages, coach pages | P0/P1/P2 | Sun 25 | ⬜ | | | | Brief extended 20 Oct (steps 7–16); simple Coach and Mentor screens already exist from the profile pass: UI only, with no cohort, item-status or moderation logic, so rule 15 is not yet implemented |
| P12 | Coach and officer views, funnel, roles, guided tour, content library, visit brief | P0 | Mon 26 | ⬜ | | | | Gate 2; depends on P11 |
| P13 | Evals (including 11), red team, cost, latency | P0 | Tue 27 | ⬜ | | | | |
| P14 | Real-scenario hardening | P0 | Tue 27 | ⬜ | | | | |
| P15 | Production deploy and freeze | P0 | Wed 28 | ⬜ | | | | Freeze |
| P16 | Submission pack | P0 | Thu 29 – Fri 30 | ⬜ | | | | |
| P17 | Sprite system (SVG items, mats, avatars, topic packs, call 11) | P0 | built ahead 22 Oct | 🟡 | 2026-10-22 | 2026-10-22 | [report](reports/SPRITES.md) | Built and tested; coach approval and officer enablement of the shipped pack, a live run of call 11 and a real-phone look are open |

## Sprite system (P17) components

| Component | Status | Evidence |
| --- | --- | --- |
| Grammar and renderer (Python, TypeScript) | ✅ built | `tests/sprites/test_grammar.py`; `apps/pwa/src/sprites/golden.test.ts` (114 parity cases) |
| Layouts (ten, counts 0 to 100) | ✅ built | `tests/sprites/test_layouts.py` |
| Avatars and expressions (code table) | ✅ built | `tests/sprites/test_avatar.py`; `tests/practice/test_faces.py` |
| Packs (`place-value-add-sub`, `fractions-demo` as JSON only) | 🟡 built; approval pending | `tests/sprites/test_packs.py`, `test_extensibility.py` |
| Authoring call 11 | 🟡 built, no live run | `tests/sprites/test_authoring.py` |
| PNG path (`resvg-py`) and channels | ✅ built | `tests/sprites/test_channels.py` |
| Contact sheet | ✅ generated | `docs/evidence/sprites/contact-sheet.png`, `.json` |

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
| Seema | One-minute probes per stage (`strings/*.json`, `stage.probe.*`), sample lines per move (including common mistakes), the new strategy lines and practice levels | P08 | no | content/ |
| Shivani | Hindi terms for borrowing or regrouping and the two strategies; whether the textbook teaches them; the PV-REVERSE stage rule (OD-21, OD-23, OD-24) | P08 | yes (English placeholders) | content/ |
| Gopi | Hourly cap for live demo runs (OD-19) once the cost per Watch run is measured | P08 | no | DECISIONS.md |

## Added 21 Oct (addendum v3.1): where the tasks went

Spec: `docs/design/addendum-v3.1.md`; synthetic sheets: `docs/build/synthetic-sheets-stage-addendum.md`; decisions: DECISIONS.md (21 Oct) and OD-18 to OD-25. Tasks for changes aimed at done phases (P04 to P07) sit in P08, the next open phase.

| Phase | New tasks | Added effort | P0 part |
| --- | --- | --- | --- |
| P08 | A1–A4 roles shell; C1–C8 demo modes and call 10; E1–E3 strategies and validator; F-a–F-d stages; G1 sheets | about 55 h | about 30 h |
| P09 | D1–D3 versions and two keys; E4–E5 strategies in tracks; F-e routines | about 9 h | about 6 h |
| P11 | A5–A6 mentor and coach inside the role system | about 2 h | 2 h |
| P12 | A7–A8 officer and production roles; B1–B3 guided tour; D4–D5 library; F-f officer stage view | about 20 h | about 11 h |
| P13 | Eval 11; eval 1 covers signatures; eval 2 re-run on call 1 v2 | about 3 h | 3 h |

**Calendar risk.** The addendum adds about 89 h (about 52 h for the P0 parts alone) to a build that already had little slack: P05 closed 🟡 on 20 Oct, P06 and P07 are 🟡, and P08 to P16 are untouched with 10 days left. P08 as written is a two-day phase. Cut items 17 to 24 first (BUILD_PROMPTS cut list); if P08 is not finished by Sat 24 Oct, move Watch's polish (C6 to C8) and F-d to after P12 and keep A1–A4, C1–C5, E1–E3, F-a–F-c and G1.

## AI gaps (22 Oct, `docs/build/reports/AI-GAPS.md`)

| Item | Status | Notes |
| --- | --- | --- |
| Citations on call 4 (method card) | Specified | Two passes (the API refuses citations with structured output). Tasks C4-1 to C4-3 in P11. API-level check PASS in the proof file |
| Citations on call 5 ("Why this move") | Specified | Evidence digest as six cached documents; tasks C5-1 to C5-4 in P09 |
| `scripts/ai_proof.py` | ✅ Built and run 22 Oct | Five checks, all PASS in `docs/evidence/ai_usage_proof.json`; re-run before submission |
| `AI_USAGE.md` and its doc test | ✅ Built | `scripts/gen_ai_usage.py` regenerates section 4; `tests/test_ai_usage_doc.py` keeps statuses honest |

## Open decisions from kit v3 (defaults apply; see DECISIONS.md)

| ID | Question | Default | Needed by | Owner |
| --- | --- | --- | --- | --- |
| OD-11 | How judges see the teacher flow | Real flows in the PWA's judge mode on simulated data, and the same flows in Telegram with `/start judge` | P05 | Gopi |
| OD-12 | Time caps | Teacher at most 20 min a week, mentor 30, coach 30 (was reviewer 15; see OD-15); revisit with round 4 data | P10 | Seema |
| OD-13 | Who holds the coach (reviewer) and officer roles in the pilot | Seema holds both; a DIET faculty member or head teacher takes one if they agree | P12 | Seema |
| OD-14 | Pilot roll numbers | Unique roll number from the register on each sheet; Seema confirms the register is stable between tests | Pre-test day | Seema |
| OD-15 | Who is the coach, and the 30-minute cap | Reviewer extended; assigned per cohort; cap 30 | P11 | Seema |
| OD-16 | Post- or pre-moderation of the cohort thread | Post-moderation with filters and Report | P11 | Gopi |
| OD-17 | Thread retention | 30 days after close, max 90 days after the last post; 7 days for held posts | P11 | Gopi |
| OD-18 | Live demo-teacher runs with recorded fallback | Live under the hourly cap and budget; recorded runs on failure, a turn over 8 s, or the cap | P08 | Gopi |
| OD-19 | Live-run cap per hour in judge mode | Set from the P04 cost per run and recorded in DECISIONS | P08 | Gopi |
| OD-20 | Tour order | Check first | P12 | Gopi |
| OD-21 | PV-REVERSE stage rule | Input (test) if confined to items 1–2; Output if computed answers are also reversed | P08 | Shivani |
| OD-22 | Stage-routine threshold and length | ≥ 25% of children checked (≥ 10 checked); ≤ 60 s | P09 | Seema |
| OD-23 | Hindi terms for borrowing or regrouping, decomposition, compensation | Placeholders until confirmed | P08 | Shivani |
| OD-24 | Does the state textbook teach decomposition and compensation? | Assume not; label as added strategies | P08 | Shivani |
| OD-25 | Programme officer weekly time cap | None set; measure in round 4 (added by Claude, not on Gopi's list) | P12 | Seema |

## Environments (no secrets here)

| Environment | URL | Last deploy | Notes |
| --- | --- | --- | --- |
| Staging | | | |
| Production | | | |
| Telegram bot | @… | | |

## Cuts taken

| Date | Cut | Why | Moved to |
| --- | --- | --- | --- |
