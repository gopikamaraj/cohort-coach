---
name: build-status
description: Show a concise status of the Cohort Coach build - phases, gates, blockers, human to-dos by owner, budget, and the next three actions. Use when the user asks where things stand, what is left, or what they need to do.
---

# Build status

Read `docs/build/PROGRESS.md`, the latest report in `docs/build/reports/`, and `docs/build/DECISIONS.md` (open decisions). Run `python tasks.py budget` if the command is available. Do not change any file.

Report, in this order and briefly:

1. **Date and runway:** today's date, days to the 31 Oct submission, days to feature freeze (28 Oct).
2. **Phases:** one line per phase that is in progress, blocked, failed or overdue (target date passed and not ✅). Then one line saying how many are done.
3. **Gates:** each gate with status and due date.
4. **Open handoff:** the Handoff block, if any, word for word.
5. **Waiting on people:** TODO-HUMAN items grouped by owner (Gopi, Seema, Shivani), each with the phase that needs it.
6. **Budget:** spent, remaining before the judging reserve, and the reserve.
7. **Risk:** if the schedule is slipping, which cut-list items in `docs/build/BUILD_PROMPTS.md` would recover the time, in order.
8. **Next three actions:** concrete, each with an owner.
