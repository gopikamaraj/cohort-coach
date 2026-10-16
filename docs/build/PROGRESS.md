# Build progress

<!-- HANDOFF: when the loop stops, it writes this block. Delete it once acted on. -->
> **Handoff** — *none open*
> - Where we are:
> - Next step:
> - Needed from people: 1. … (owner)
> - Resume with: `/next-phase`

**Today:** 2026-10-16 · **Days to submission (31 Oct):** 15 · **Budget spent:** USD 0.00 of 350 (judging reserve 150 untouched)

## Phases

Status: ⬜ not started · 🔄 in progress · ✅ done · 🟡 done with non-blocking gaps · ❌ failed · ⛔ blocked · ✂️ cut

| ID | Phase | Priority | Target | Status | Started (commit) | Finished | Report | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | Bootstrap, inventory, decisions | P0 | Fri 16 Oct | ✅ | 2026-10-16 14:46 (`ac4a940`) | 2026-10-16 | [report](reports/P00-bootstrap.md) | CI green on `83e571b` (run 38881893876) |
| P01 | Engine core | P0 | Fri 16 – Sat 17 | ⬜ | | | | |
| P02 | Simulated block, grouping, mentors, statistics | P0 | Sat 17 | ⬜ | | | | |
| P03 | AI platform and guardrails core | P0 | Sun 18 | ⬜ | | | | |
| P04 | Practice Class engine + calls 1–3 (text) | P0 | Mon 19 | ⬜ | | | | Gate 1 |
| P05 | PWA shell, judge mode, check entry, error cards | P0 | Tue 20 | ⬜ | | | | |
| P06 | Practice Class UI, overlay, staging | P0 | Wed 21 | ⬜ | | | | Staging |
| P07 | Voice | P0 | Thu 22 | ⬜ | | | | |
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
| Gate 1: SUB-SFL text rehearsal end to end | Mon 19 Oct | ⬜ | |
| Staging live for test round 3 | Wed 21 Oct | ⬜ | |
| Gate 2: all storyboard screens on a low-end phone | Mon 26 Oct | ⬜ | |
| Freeze: production smoke-tested | Wed 28 Oct | ⬜ | |
| Submitted | Sat 31 Oct | ⬜ | |

## Waiting on people (TODO-HUMAN)

| Owner | Item | Needed by phase | Placeholder in place? | File |
| --- | --- | --- | --- | --- |
| Gopi | Telegram bot reuse paths (optional; default build fresh) | P10 | yes | DECISIONS.md |
| Gopi | Install ffmpeg (`winget install Gyan.FFmpeg`); Sarvam account + key in `.env` | P07 | n/a | — |
| Gopi | Make repo public before submission (`gh repo edit --visibility public`) | P16 | n/a | — |

## Environments (no secrets here)

| Environment | URL | Last deploy | Notes |
| --- | --- | --- | --- |
| Staging | | | |
| Production | | | |
| Telegram bot | @… | | |

## Cuts taken

| Date | Cut | Why | Moved to |
| --- | --- | --- | --- |
