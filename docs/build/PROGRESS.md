# Build progress

<!-- HANDOFF: when the loop stops, it writes this block. Delete it once acted on. -->
> **Handoff** — P06 built; staging needs you; P07 can start
> - Where we are: P06 🟡 (Practice Class screen, AI-layers overlay, AI map, audit viewer, degraded states, round 3 kit, staging recipe). Staging is not deployed. ffmpeg (9.0.2) and `SARVAM_API_KEY` are in place, so P07 (voice) can start.
> - Needed from people: 1. Create hosting accounts and run `docs/deploy.md` for staging; put the URLs under Environments below (Gopi). 2. Seema runs round 3 with `docs/user-testing/round3-script.md`; Shivani reviews the Hindi. 3. Listen to the five child voices when P07 is done and confirm (Gopi).
> - Resume with: `/next-phase`

**Today:** 2026-10-17 · **Days to submission (31 Oct):** 14 · **Budget spent:** USD 0.52 of 350 (judging reserve 150 untouched)

## Phases

Status: ⬜ not started · 🔄 in progress · ✅ done · 🟡 done with non-blocking gaps · ❌ failed · ⛔ blocked · ✂️ cut

| ID | Phase | Priority | Target | Status | Started (commit) | Finished | Report | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | Bootstrap, inventory, decisions | P0 | Fri 16 Oct | ✅ | 2026-10-16 14:46 (`ac4a940`) | 2026-10-16 | [report](reports/P00-bootstrap.md) | CI green on `83e571b` (run 38881893876) |
| P01 | Engine core | P0 | Fri 16 – Sat 17 | ✅ | 2026-10-16 15:30 (`f92f846`) | 2026-10-16 | [report](reports/P01-engine-core.md) | CI for this phase after push; Seema to confirm key variants |
| P02 | Simulated block, grouping, mentors, statistics | P0 | Sat 17 | ✅ | 2026-10-16 20:45 (`a0d858f`) | 2026-10-16 | [report](reports/P02-simulated-block-statistics.md) | CI for this phase after push; demo cohorts small by design |
| P03 | AI platform and guardrails core | P0 | Sun 18 | ✅ | 2026-10-16 (`9bfc51c`) | 2026-10-17 | [report](reports/P03-ai-platform-guardrails.md) | Live red team on 12 seeds passed; cache hits confirmed |
| P04 | Practice Class engine + calls 1–3 (text) | P0 | Mon 19 | 🟡 | 2026-10-17 (`6b18369`) | 2026-10-17 | [report](reports/P04-practice-class-engine.md) | Gate 1 end-to-end passed; text-turn latency over 3 s (plan in report) |
| P05 | PWA shell, judge mode, check entry, error cards | P0 | Tue 20 | ✅ | 2026-10-17 (`6306eb7`) | 2026-10-17 | [report](reports/P05-pwa-shell-check-cards.md) | Installable, offline T1–T3, 3 languages, bundle 112 kB |
| P06 | Practice Class UI, overlay, staging | P0 | Wed 21 | 🔄 | 2026-10-17 (`0e57872`) | | | Staging |
| P07 | Voice | P0 | Thu 22 | 🔄 | 2026-10-17 (`874d069`) | | | |
| P08 | Answer-sheet capture and import | P0/P1 | Fri 23 | ⬜ | | | | |
| P09 | Content pipeline | P0 | Sat 24 | ⬜ | | | | |
| P10 | Telegram channel | P0 | Sun 25 | ⬜ | | | | |
| P11 | Mentor loop | P1 | Sun 25 | ⬜ | | | | |
| P12 | Officer and outcome views | P0 | Mon 26 | ⬜ | | | | Gate 2 |
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
| Gopi | Telegram bot reuse paths (optional; default build fresh) | P10 | yes | DECISIONS.md |
| Shivani, Gopi | Review hi/ta/Hinglish profanity lists; full 50 red-team prompts | P13 | yes (12 seeds) | content/safety/, evals/sets/redteam.yaml |
| Seema, Gopi | Native review of hi/ta number words, jargon, error names, badge and explanation wording | P09 | yes (drafts) | content/lang/, ai/guard/ |
| Shivani | Review Hindi UI strings (`python scripts/i18n.py export`) | P06 | yes (draft) | apps/pwa/src/i18n/hi.json |
| Gopi | Review Tamil UI strings; confirm P05 DECISIONS | P06 | yes (draft) | apps/pwa/src/i18n/ta.json |
| Seema | Review P04 move lists, rubrics, scenario values, personas and hi/ta templates | P06 | yes (drafts) | content/ |
| Shivani | 150 labelled lines for the labeller eval; realism ratings; 50 red-team prompts | P13 | no | evals/sets/ |
| Gopi | Make repo public before submission (`gh repo edit --visibility public`) | P16 | n/a | — |
| Seema | Review fictional teacher names | P05 | yes (draft list) | content/personas/teachers_simulated.yaml |
| Seema | Confirm extra heard-and-reversed variants (3064, 300604) and NCERT match of the 20 items | P04 | yes | docs/engine.md |

## Environments (no secrets here)

| Environment | URL | Last deploy | Notes |
| --- | --- | --- | --- |
| Staging | | | |
| Production | | | |
| Telegram bot | @… | | |

## Cuts taken

| Date | Cut | Why | Moved to |
| --- | --- | --- | --- |
