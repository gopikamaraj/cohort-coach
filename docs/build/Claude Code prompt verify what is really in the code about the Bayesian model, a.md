# Claude Code prompt: verify what is really in the code about the Bayesian model, and how the simulated child works

Paste everything below the line into Claude Code at the repo root. This is a **read-only** investigation. It writes one report.

---

**Task.** Settle, from the code, what the repository actually implements for the simulated child and for anything described as "Bayesian", "belief", "latent state" or "probabilistic". Our decks say: the simulated child is **seeded and rule-based** (`engine/simulator.py`), and the **Bayesian child model and belief engine are planned, not built**. Prove or correct that. Then describe exactly how one Practice Class turn works, with the real constants.

## Rules

- **Read-only.** Change no code, config, content or data. The only file you create is `docs/build/reports/BAYESIAN-CHECK.md`. Scratch scripts go in `/tmp` and are not committed.
- **No secrets, no paid or external calls.** Never print environment variable values. Do not call the AI or voice services. Run only offline code and tests.
- **Evidence for every statement:** a file path and line numbers, a test name, or a command and its output. Do not guess.
- **Three honest statuses only:**
  - **Built:** implemented in code that runs, with a test or a call site.
  - **Described only:** named in documents, prompts, comments or slides, with no implementing code.
  - **Not found.**
- A function that exists but is never called is **Built, unused**, and say so.

## Step 1. Find every mention

Search the whole repository (code, content, docs, prompts, tests, slides and the untracked `apps/pwa-v2/`) for these words, case-insensitive, and list each hit as file, line and a short quote:

`bayes`, `bayesian`, `posterior`, `prior`, `likelihood`, `belief`, `latent`, `hidden state`, `hmm`, `markov`, `pomdp`, `knowledge tracing`, `bkt`, `dina`, `repair theory`, `32 state`, `information gain`, `entropy`, `sigmoid`, `logistic`, `forgetting`, `retention`, `priming`, `attention`, `mood`, `learning rate`, `slip`, `guess`, `golden`, `oracle`, `MODEL.md`, `SPEC.md`.

Group the hits into: implementing code, tests, content files, documentation and prompts, and decks or reports. Say which hits are only descriptions.

## Step 2. What the simulated child is today

Read `engine/simulator.py`, the tests (`tests/engine/test_simulator.py`, `test_simulator_stages.py`, `tests/practice/test_session.py`, `test_recorded_session.py`), `content/` for children, moves, scenarios and sprites, `services/practice/`, and the calls `ai/calls/c01_child_voice.py`, `c02_move_label.py`, `c03_feedback.py`, `c07_*`. Then answer, with evidence:

1. **State.** What does a simulated child store? List every field and its type and range (for example error strength, error type, stage, attention, mood, memory, any per-skill value).
2. **Profiles.** How many children are in a class, and how are their levels and errors set? From where (a class's own data, a scenario file, fixed profiles)? Show the actual values.
3. **A turn, step by step.** Starting from the teacher's input, trace every function called, in order, to the child's spoken line: speech to text, the move label, the engine update, the answer choice, the line, the checker, the voice, and the feedback at the end of a session. Give the file and line of each step.
4. **The move effect.** What is the list of move labels? For each label, exactly how does the engine change the child (which fields, by how much, in which direction, under what condition)? Print the table. If a label has no effect, say so.
5. **The answer rule.** How is a wrong or right answer chosen? Is it `random() < error_strength`? How is the wrong number produced (which bug function)? Is the random number generator seeded per session or per child, and how?
6. **Stages.** What is a stage in `test_simulator_stages.py`, what do the 12 tests check, and what is the "stage signature" in `docs/evidence/stage_signature_check.md`?
7. **Mood and face.** How does the engine decide the expression or mood the avatar shows? Is it computed from state, or set by the AI?
8. **Learning over a session.** Can a child "understand" during a session, and how is that represented? Is there memory across turns, across sessions, or across days?
9. **Determinism.** Run a small offline script (in `/tmp`) that creates a class with a fixed seed, applies a fixed sequence of move labels, and prints each child's state and answer after every turn, twice. Confirm that the two runs are identical, and that a different seed gives different output. Paste the printed table into the report.
10. **Sensitivity.** Using the same script, change each important constant (for example error strength, any move effect size) by about 20 percent and report whether the order of which move helps most changes. This answers a question the technical mentor raised.
11. **Tests.** Run the simulator and practice tests offline and report the counts and any failures. Run `evals/runners/sim_fidelity.py` offline if it needs no network, and report what it asserts.

## Step 3. Is anything Bayesian actually in the code?

For each element of the designed Bayesian model, give a status (Built, Built but unused, Described only, Not found) with evidence. Use the design document (`MODEL.md` or wherever it lives) as the checklist, and say where you found it.

| Element of the design | Status | Evidence |
| --- | --- | --- |
| Hidden variables for place value, the exchange idea, the written borrowing step, and a wrong habit |  |  |
| A state space of 32 combinations (2 × 2 × 2 × 4) |  |  |
| A response model: a probability table mapping state and item to an answer |  |  |
| Teaching transitions by a logistic function of coverage, fit, scaffolding, attention and overload |  |  |
| Attention dynamics (a low-pass filter with a time constant) |  |  |
| Memory: a forgetting curve, and priming after a demonstration |  |  |
| A belief engine: a probability for each state, updated by Bayes' rule from answers |  |  |
| Choosing the next question by expected information gain |  |  |
| Soft evidence from a teacher's note |  |  |
| Parameter uncertainty bands |  |  |
| Golden tests G1 to G7, and an independent oracle script that checks them |  |  |
| Behaviour tests B1 to B8 over many seeds |  |  |
| Exemplar replay on the same class and seed |  |  |

Also check the **verdict statistics** (`engine/statistics*` or similar). Say precisely what method it uses (bootstrap over classes, exact McNemar, anything with a prior or a posterior), because it is statistics, and it must not be confused with a Bayesian child model.

## Step 4. Where our claims may be wrong

Search these places for the words "Bayesian", "belief", "hidden state", "32", "probability table", "hand-specified" and "learning by chance", and for any claim that the child "learns", "has attention", or "forgets":

- the decks and any exported slide files in the repository,
- `docs/RUBRIC_MAP.md`, `AI_USAGE.md`, `README.md`, `DECISIONS.md`, `docs/help/*.md` and the assistant's content,
- UI strings in `apps/pwa/src` and `content/`,
- the judge guide's source documents.

For each place, give the claim, whether the code supports it, and a one-line corrected wording that matches the code. List the places where the code is **stronger** than the claim, too.

## Step 5. A true description for the deck and the video

At the end of the report, write two short pieces, using only what you verified:

1. **150 words** describing how the simulated child works today, in plain language a teacher and a technical reviewer could both follow, with no claim the code does not support.
2. **One paragraph** saying what the Bayesian model would add, what it is not yet, and what would be needed to build and validate it (a written specification, educator review, sensitivity analysis, tests against real classrooms, and a separate evaluation of the move classifier).

## Step 6. The report

Write `docs/build/reports/BAYESIAN-CHECK.md` with these sections: summary (five lines: is anything Bayesian built, yes or no), Step 1 hits, Step 2 findings with the printed tables, Step 3 status table, Step 4 corrections, Step 5 wording, and a list of open questions you could not settle from the code.

Finish by printing the summary and the Step 3 table in the chat.

**Done when** the report exists, every statement carries evidence, the determinism and sensitivity runs are included, and no file other than the report has changed (confirm with `git status`).
