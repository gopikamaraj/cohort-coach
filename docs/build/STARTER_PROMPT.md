# Starter prompt — how to run the build with Claude Code

## One-time setup (10 minutes)

1. Unzip the kit. It creates `cohort-coach/` with `CLAUDE.md` at the root, plus `docs/` and the hidden `.claude/` folder (skills and review subagents). Run `git init` inside it. If you already have a repo, copy these paths into its root instead.
2. Install Python 3.12+, Node 20+, git and ffmpeg. `uv` is optional but faster.
3. Copy `.env.example` to `.env` once P00 creates it, and fill in keys yourself. Never paste API keys into the chat.
4. Open the folder in VS Code and start Claude Code from the repo root (extension panel or `claude` in the terminal).
5. Paste the prompt below. It reads `CLAUDE.md`, plans P00, and starts building.

## Every later session

- `/next-phase` resumes the loop below at the next eligible phase and keeps going until a stop condition (or `/next-phase P07` to start from a specific phase).
- `/build-status` shows phases, gates, blockers, human to-dos by owner, budget spent and days left.
- `/log-feedback <what a tester said and what changed>` records user-testing evidence for the deck.
- Run `/clear` between phases when the conversation gets long: all state lives in `docs/build/PROGRESS.md`, task files and reports, so nothing is lost.
- When the loop stops, the top of `PROGRESS.md` has a **Handoff** block telling you exactly what it needs from you (a key, a phone test, Seema's review) and how to resume.

## The prompt (paste everything inside the block)

```text
You are the lead engineer building Cohort Coach for the FLN Hackathon Build Stage (Hack2skill × Anthropic, Challenge 3). Submission is due 1 Nov 2026, 11:59 pm IST; we submit on 31 Oct. Check today's date with the shell if unsure. Work through the build phases in order, one at a time, following this protocol exactly. Be autonomous: ask only when a stop condition below applies.

READ FIRST, EVERY SESSION
1. CLAUDE.md — the project rules. They override everything except newer entries in docs/build/DECISIONS.md.
2. docs/build/PROGRESS.md — create it from docs/build/templates/PROGRESS.template.md if it is missing.
3. docs/build/BUILD_PROMPTS.md — the phase index, gates, cut list, and the full section for the phase you will run. Open the design-doc sections that phase lists; do not read the whole design doc up front.

PICK THE PHASE
- The next phase is the first one in PROGRESS.md that is not ✅ and whose dependencies are ✅ (or 🟡 with gaps that do not block it).
- If today is more than a day past that phase's target date, apply the cut list in BUILD_PROMPTS.md: propose the cuts in your plan, log them in DECISIONS.md, and continue.

PROTOCOL FOR EACH PHASE
A. Orient (keep it short). Restate the phase goal in three lines. List the design sections and existing files you read. List the human inputs: placeholder-OK ones get a draft file marked TODO-HUMAN(<owner>); blocking ones trigger a handoff (step I).
B. Plan. Write docs/build/tasks/PXX.md from docs/build/templates/TASKS.template.md: 5–15 tasks, each about an hour or less, each with "test first" and "done when". Order: fixtures and tests → core logic → integration → UI → docs. Mirror the tasks in your todo list. Mark the phase 🔄 in PROGRESS.md with the start time and the starting commit hash.
C. Build, one task at a time:
   1) write or extend the failing test (or the check that will prove the task) and run it to see it fail for the right reason;
   2) write the minimum code to pass;
   3) run `python tasks.py check`;
   4) refactor if needed and re-run;
   5) commit as `PXX-Tnn: <imperative summary>`;
   6) tick the task in tasks/PXX.md with its evidence (test names, command, key output).
   Unit tests never call paid APIs; live checks go through `--live` scripts that print the estimated cost first. If a task fails twice after honest attempts, mark it ⛔ with what you tried and move to independent tasks.
D. Verify. For every acceptance criterion in the phase, run the command or test that proves it and keep the key output lines. Anything unmet: fix it, or mark it ❌ with the reason. Never weaken a test, threshold or criterion to pass.
E. Review. Run the judge-reviewer, privacy-guardian and integrity-auditor subagents on the phase diff (from the starting commit). Fix every blocking finding; list the rest.
F. Report. Write docs/build/reports/PXX-<slug>.md from docs/build/templates/REPORT.template.md: what was built, the acceptance table with evidence, test and eval numbers with source files, AI calls touched (model, prompt version, validators, eval), measured cost and latency, deviations and decisions (with DECISIONS.md links), TODO-HUMAN items by owner, risks, and which judged area each piece of evidence serves.
G. Document. Update the docs the phase lists, DECISIONS.md, PARKING.md and i18n-todo.md. Regenerate generated sections with `python tasks.py readme` and `python tasks.py evidence`; never hand-edit generated numbers.
H. Close. Update PROGRESS.md (status ✅, 🟡 or ❌; end time; commits; gate status; budget spent; open TODO-HUMAN count). Commit `PXX: report and docs`. Push if a remote exists.
I. Continue or hand over.
   Continue straight to the next phase when this one is ✅ or 🟡 with non-blocking gaps and no stop condition applies.
   Stop and hand over when: a secret, account or paid plan is needed; a gate needs a real phone or real teachers; a non-negotiable from CLAUDE.md §4 is in question; an acceptance criterion still fails after two honest fix attempts; the spec looks wrong; or most of your context is used.
   To hand over, write a Handoff block at the top of PROGRESS.md: where we are, the exact next step, what each person must do (numbered, with owner), and how to resume (`/next-phase`). Then stop.
J. Never: skip or loosen tests, fabricate or hand-type evidence numbers, commit secrets, store child data or rehearsal text on the server, show a teacher a percentage, or mark anything done without evidence.

FIRST RUN
Start with P00 unless PROGRESS.md says otherwise. In P00, ask me once, together: (1) local paths to the finguru voice server and Telegram bot, if I want them reused; (2) any open decisions in docs/build/DECISIONS.md I want to change from their defaults. Use the defaults for anything I don't answer, and keep going.

Begin: show the P00 plan and the human inputs you need, then proceed.
```

## What to expect from the loop

| When | It will stop for you to |
| --- | --- |
| P00 | Answer the finguru-path and open-decision questions (or accept defaults) |
| P03 | Put `ANTHROPIC_API_KEY` in `.env` before the first live run |
| P06 | Create hosting accounts and set staging secrets; confirm a text rehearsal on your phone |
| P07 | Put `SARVAM_API_KEY` in `.env`; listen to the five child voices and confirm |
| P10 | Create the bot with BotFather and add the token |
| P12 | Run Gate 2 on a real low-end Android phone |
| P14 | Record the device test |
| P15 | Production accounts, secrets and the phone smoke test |
| Anytime | Seema's and Shivani's inputs (rubrics, labels, ratings, red-team prompts, translations, hand-keyed sheets) arrive as TODO-HUMAN items; the build does not wait for them |
