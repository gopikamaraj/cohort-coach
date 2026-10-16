---
name: log-feedback
description: Record user-testing feedback in docs/feedback-log.md as evidence for the "User inputs and testing" judging criterion. Use when the user reports what a teacher, tester, HM or officer said or did, or what was changed because of it.
---

# Log feedback

Input: `$ARGUMENTS`, free text from the user, for example: "round 3, T04 said the children talk too fast in Hindi; we slowed TTS".

1. Extract: date (default today), round (1 real check, 2 concept interviews, 3 Practice Class usability, 4 voice lesson and mentor capture, pilot, or other), participant code, what they said or did (keep their words when quoted; translate to English in brackets if not English), what we changed (if anything), status (changed, planned, won't change with reason).
2. Privacy: never store a person's name, school name or phone number. Convert names to codes (T01, T02… for teachers; HM01… for headteachers; O01… for officers) and keep the mapping out of the repo. If the user gave a name, tell them you replaced it with a code.
3. If a change was made, find the commit: use the hash the user gave, or search `git log` for the related change and confirm with the user if unsure. Link it as `` `abc1234` ``.
4. Append one row to the table in `docs/feedback-log.md`. If nothing changed yet, set status "planned" and add a line to the relevant phase's tasks file, or to `docs/build/PARKING.md` if no phase fits.
5. If the feedback reports a safety problem or a wrong AI output, also add it to the red-team or eval set it belongs to (`evals/sets/…`) as a new case, marked with its source round and code.
6. Run `python scripts/feedback_table.py` if it exists, so the deck's "You said → We changed" table stays current. Commit as `feedback: <round> <participant code> <short summary>`.

Ask a question only if the round or what was said is missing.
