---
name: next-phase
description: Run the Cohort Coach build loop for the next eligible phase (or the phase named in the arguments, e.g. "P07"), following the protocol in docs/build/STARTER_PROMPT.md. Use when the user says next phase, continue the build, or resume.
---

# Run the next build phase

1. Read `CLAUDE.md`, `docs/build/PROGRESS.md` and the "PROTOCOL FOR EACH PHASE" section (steps A–J) inside the prompt block of `docs/build/STARTER_PROMPT.md`.
2. If a Handoff block is open at the top of `PROGRESS.md`, check whether its human steps are done (look for the keys in `.env` by name only, the files, or the confirmations it asked for). If they are not, list what is still missing, briefly, and stop.
3. Choose the phase:
   - If arguments were given (`$ARGUMENTS`, e.g. `P07`), use that phase, but only if its dependencies in `docs/build/BUILD_PROMPTS.md` are ✅ or 🟡 with non-blocking gaps; otherwise say which dependency is missing and stop.
   - Otherwise pick the first phase in `PROGRESS.md` that is not ✅ and whose dependencies are met.
4. Run steps A–I of the protocol for that phase, exactly as written, including the subagent reviews, the report, the docs and the `PROGRESS.md` update.
5. At step I, continue to further phases only if no stop condition applies; otherwise write the Handoff block and stop.

Start by printing one line: the phase you are running, its target date, and days left to the 31 Oct submission.
