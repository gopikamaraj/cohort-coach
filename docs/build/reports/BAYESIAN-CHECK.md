# Bayesian check: what the code really does for the simulated child

Run on 1 Nov 2026, read-only. No code, config, content or data changed; this file is the only one written. Everything was run offline: no AI call, no voice call, no network. The two scratch scripts (determinism, sensitivity) were run from a scratch folder outside the repository and are described below, with their printed output.

## Summary

1. **Is anything Bayesian built? No.** No prior, posterior, likelihood, belief state, hidden Markov or knowledge-tracing code exists anywhere in the repository. The words appear only in build prompts and one status report, as something planned.
2. **The simulated child is seeded and rule-based**, as the decks say. A child holds one number, an error *strength* (0.9 at the start), plus an engagement number and a few counters. A move subtracts a fixed amount from strength. A wrong answer is chosen when `random() < strength`, and the wrong number always comes from the bug function (`engine/simulator.py:345-347`).
3. **The child does not "understand" in any richer sense.** Her strength falls by the same amount whatever the child just answered, whatever her engagement, and whatever else was said. There is no attention, forgetting, priming, or memory beyond the session.
4. **Two parts are more than the decks say, in a good way:** four stages of breakdown (core, input-teaching, input-test, output) change *how* a child errs, and a class-shared "overhear" and chorus (up to three children speak a turn). Both are tested.
5. **Two things to correct or watch:** the move that sets everything in motion is **chosen by an AI labeller** (call 2, whose eval is still pending), so "rule-based" holds for the child, not for what the teacher's words are taken to mean; and the three strongest moves are **tied** by construction, so "which move helps most" is just the order of the numbers in the move list.

## Step 1. Every mention

Searched the whole repository (code, content, docs, prompts, tests, slide text in `docs/submission/`, both apps including the untracked `apps/pwa-v2/`), excluding `node_modules`, `.venv`, build output and caches. Command shape: `grep -rniE "<terms>" . --exclude-dir=...`.

| Term | Hits that matter | Kind | What it is |
| --- | --- | --- | --- |
| bayes / bayesian | `docs/build/Claude Code prompt the end-to-end demo flow (Demo Studio).md:48` ("Generate the children from the Bayesian child model"); `docs/build/reports/STACK.md:52,146,188` ("Planned, not built"); `docs/build/reports/QA-DEMO.md:120`; `docs/build/Claude Code prompt full demo QA...md:37,42,79`; `apps/pwa/e2e/demo-path.spec.ts:162` (a test that the app never says it) | prompts, reports, one test | Described only. No implementing code |
| posterior, belief, hidden state, markov, pomdp, knowledge tracing, dina, repair theory, 32 state, information gain, entropy, sigmoid, logistic, priming, learning rate | none in code, content or tests (only `docs/design/evidence-digest.md:109` "Knowledge, beliefs", about teachers) | — | Not found |
| latent | `data/synthetic/block.py:3,49,81,99-136,157-279` | implementing code | A child's hidden *set of error codes*, drawn from planted counts with `random.Random`. Used by the simulated block and the demo class, not by the Practice Class |
| likelihood | `docs/build/templates/REPORT.template.md:63` | template | The word "Likelihood" in a risk table |
| forgetting | `content/lang/error_names.yaml:12` | content | "forgetting the carried ten": the name of an error, not a forgetting curve |
| slip | `data/synthetic/block.py:128-135` (`_slip`, `slip_rate: 0.07` in `data/synthetic/config.yaml:28`) | implementing code | A random one-off wrong answer in the synthetic block. Not a BKT slip parameter |
| oracle | `evals/runners/engine_items.py:4-107`, `evals/runners/sim_fidelity.py:49` | evals | An independent digit-by-digit computation of the bug functions' wrong answers, to check the engine. Not a checker for any probabilistic model |
| golden | `docs/design/pilot_forms.golden.json`, `engine/export_keys.py` golden diagnosis cases | data, code | Golden test cases for the answer keys, not "G1 to G7" |
| retention | data-retention settings and tests | code, docs | Deleting data after N days; unrelated |
| attention, mood, engagement | `engine/simulator.py:192,229,361-368,426,437,497`; `content/movelists/*.yaml` `engagement:`; `ai/calls/c01_child_voice.py:39`; `services/practice/faces.py` | implementing code | Engagement and mood are built (see Step 2). "Attention" appears only in teacher lines ("pay attention!") |
| `MODEL.md`, `SPEC.md` | `MODEL.md`: none. `SPEC.md`: only in two prompts and the Stitch pack index, as an unrelated word | — | **There is no design document for a Bayesian model in the repository.** The checklist in Step 3 comes from the task prompt |
| hmm, bkt | hits are hexadecimal ids in JSON fixtures and one "Hmm." in a recorded demo line | — | Not relevant |

**Grouped:** implementing code (`engine/simulator.py`, `data/synthetic/block.py`, `services/demo/scenario.py`, `services/practice/*`), tests (`tests/engine/test_simulator*.py`, `tests/practice/*`), content (`content/movelists`, `content/scenarios`, `content/personas`), documentation and prompts (the prompts and reports above), decks (`docs/submission/deck.md`, `slides.md`, `video-script.md`: no mention of Bayesian). The only "described only" hits are the prompts and reports.

## Step 2. What the simulated child is today

### 2.1 State (`engine/simulator.py`)

| Where | Field | Type and range |
| --- | --- | --- |
| `Child` (`:224-234`) | `name` | str (a fictional name from `content/personas/children.v1.yaml`) |
| | `error` | `ErrorCode` or None (None = a correct child) |
| | `shy` | bool: speaks only when named |
| | `strength` | float 0 to 1 (clamped, `_clamp` `:273`); 0.9 at the start for a child with an error, 0 for a correct one (`:283`) |
| | `engagement` | float 0 to 1; starts at 0.6 (`start_engagement`) |
| | `streak` | int: consecutive correct answers |
| | `quiet_turns` | int: turns she stays quiet after a scold |
| | `last_answer`, `last_written` | int or None: the number she said and the one she wrote on her slate |
| | `stage` | one of `core`, `input-teaching`, `input-test`, `output` (`:39`) |
| `SessionState` (`:238-246`) | `seed`, `turn`, `children`, `problem`, `next_problem`, `finished`, `finished_reason` | |

There is **no** attention, mood, memory, per-skill or per-concept value stored. `mood` is a label computed each turn (2.7).

### 2.2 Profiles

- **Five children**: `n_seats=5` (`fill_seats` `:640-695`). Seat 0 is always correct. Up to four have an error.
- **Set from the class when known**: with her class's counts and number checked, the error children are `round(5 × showing / checked)` seats, split by the largest-remainder rule (`_apportion` `:698`); the target error always has a seat. Without counts, the scenario's `seat_mix` (SUB-SFL: `{SUB-SFL: 3, SUB-NODEC: 1}`, `content/scenarios/sub-sfl.v1.yaml`).
- **Stages** come from the scenario's `stage_mix`: for SUB-SFL `[core, input-test, output, core]` read down the seats after the correct one (`:690`).
- **Shy**: the last erring child when two or more have an error (`:680-684`).
- **Levels**: every child with an error starts at the *same* strength, 0.9, and engagement 0.6 (`content/scenarios/sub-sfl.v1.yaml:11-12`). The differences between children are the error, the stage and who is shy, **not a different starting level**. A "mixed level" flag (`CLAUDE.md` section 5) is **not implemented** (`grep mixed_level` finds nothing in code).
- **Names**: five distinct fictional children, 3+2 by gender, chosen with `random.Random(f"names:{seed}")` (`services/practice/session.py:177-187`).

Printed for seed 5, SUB-SFL, no class counts: Asha (correct, core), Ravi (SUB-SFL, core), Meena (SUB-SFL, input-test), Arun (SUB-SFL, output), Priya (SUB-NODEC, core, shy).

### 2.3 One turn, step by step

| # | Step | File and line |
| --- | --- | --- |
| 1 | Speech in: Sarvam speech-to-text on her recording | `services/api/practice.py:244` (`speech.transcribe`). In text mode she types and this step is skipped (`:165-169`) |
| 2 | Her line is masked: a real child's name, roll or phone number is replaced, the five pretend children's names kept | `services/practice/session.py:~308` (`mask_personal(..., keep=children)`) |
| 3 | **Move label, call 2** (AI): move id from the scenario's closed list, whom she addressed, an optional posed problem; low confidence becomes `other`; an injection becomes `off_task`; on failure `other` (and the one named child, by code) | `session.py:312` → `ai/calls/c02_move_label.py` |
| 4 | **Engine turn**: `plan_turn` applies the move's effect, picks the speaker, the problem and the answer, and builds the set of numbers a child may say | `session.py:322` → `engine/simulator.py:371-550` |
| 5 | Child's line: for kinds of line the deployment asks the AI for (`PRACTICE_AI_INTENTS`), **call 1** puts the engine's answer into a Grade 3 child's words; otherwise the engine's own template line | `session.py:328-345`; `ai/calls/c01_child_voice.py:85`; `services/practice/templates.py:23` |
| 6 | Code checks (every number in the line is in the allowed set, language, length, pre-filter), then the output checker **call 7** unless `PRACTICE_SKIP_CHECKER=1`; a failure is replaced by the template | `c01_child_voice.py:112-153`; `ai/guard/gates.py` |
| 7 | The other children who speak (chorus) say template lines built from their own engine plans | `session.py:346-357` |
| 8 | Faces: each child's expression from a code table (state in, expression out); no AI | `session.py:134,158` → `services/api/sprites/expression.py` |
| 9 | Voice out: Sarvam text-to-speech, started in parallel with the checker and released only if the line passes | `services/api/practice.py:185,280` |
| 10 | End of session: **call 3** writes two strengths and one thing to try, quoting her words; a template if it fails | `session.py:474-508` → `ai/calls/c03_feedback.py:194` |

### 2.4 The move effect

From `content/movelists/*.yaml`, applied in `plan_turn` `:413-428`. Strength is changed only for children with an error and only if the effect is non-zero; engagement changes for every child reached; `quiet` sets `quiet_turns=2` for the child reached.

SUB-SFL (the others are the first eight rows, with `regroup_ten` for ADD-NOCARRY and `show_chart` for PV-HEARD in place of `exchange_ten`):

| Move | Behaviour | Strength | Engagement | Quiet | Note |
| --- | --- | --- | --- | --- | --- |
| pose_problem | answer | 0 | 0 | no | sets the problem; child answers |
| ask_explain | explain | −0.20 | +0.05 | no | child states her working |
| show_bundles | work_aloud | −0.30 | +0.10 | no | child re-answers; steps said aloud |
| exchange_ten | work_aloud | −0.30 | +0.10 | no | |
| check_back | doubt | −0.20 | +0.05 | no | child checks by adding back |
| tell_rule | agree | −0.05 | 0 | no | |
| praise | thanks | 0 | +0.15 | no | |
| scold | quiet | 0 | −0.30 | **yes** (2 turns) | the child goes quiet and says nothing useful |
| decomposition | work_aloud | −0.30 | +0.10 | no | SUB-SFL and SUB-NODEC only |
| compensation | work_aloud | −0.25 | +0.05 | no | " |
| repeat_rule_louder | agree | −0.02 | −0.05 | no | " |
| give_the_answer | agree | 0 | −0.10 | no | " |
| order_probe | explain | −0.20 | +0.05 | no | SUB-SFL only |
| other, off_task (not in the list) | confused | 0 | 0 | no | `NEUTRAL` (`:36,382-383`): changes nothing but the turn counter |

Every effect is **unconditional**: it is applied whether or not the child answered right or wrong, whatever her stage, engagement or the problem. A move aimed at one child reaches the rest of the room at `overhear` = 0.5 of its effect on strength and engagement (never the going quiet); `chorus_max` = 3 children speak a turn.

### 2.5 The answer rule

- A child with an error in the `core` stage answers wrong when `rng.random() < child.strength` (`:345`), and the wrong number is `rng.choice(sorted(wrong_answers(error, problem)))` (`:344,346`), where `wrong_answers` (`:68-82`) calls the bug functions `sub_sfl`, `sub_nodec`, `add_nocarry`, `pv_heard`, `pv_reverse` from `engine/bugs.py`. A child with strength 0 (or the correct child) always answers right (`:358`).
- Other stages use the same probability test: `output` says the right number and writes it reversed (`:348-351`); `input-test` says the other operation's result or a digit-swapped one (`:352-355`); `input-teaching` says no number and is lost (`:356-357`).
- **Seeding is per session and turn, not per child:** `rng = random.Random(f"{state.seed}:{turn}")` (`:389`); the chorus uses `random.Random(f"{seed}:{turn}:chorus")` (`:491`), so the first speaker is the same with or without a chorus (tested). If no seed is given a session seed is drawn from `SystemRandom` (`session.py` `start_session`).

### 2.6 Stages

`STAGES = ("core", "input-teaching", "input-test", "output")` (`:39`): where a child's mistake most likely arises. The 12 tests in `tests/engine/test_simulator_stages.py` check: a core child is unchanged; an output child says the right number and writes it reversed (and writes it right once she has got it); an input-test child hears the other operation or swaps the numbers, and misreads a dictation by one digit; an input-teaching child has no method and says so without a number; materials lower strength for every stage; every number said is in the allowed set; the default seating is three core, one input-test, one output; an unknown stage is refused; no-stage-mix means all core; and a stage never changes who is in the class, only how they err.

`docs/evidence/stage_signature_check.md` is a different thing: a one-off, design-time check (21 Oct) that the wrong-answer *signatures* used by the stage-of-breakdown card (CORE-OFF1, IN-OP, OUT-REV, …) do not collide on the pilot forms' items except the designed PV-HEARD / PV-REVERSE overlap. It concerns the diagnosis of real answer sheets, not the simulator.

### 2.7 Mood and face

`_mood` (`:361-368`) is computed from state: `small` (after a scold), `doubtful` (a wrong answer under a check-back), else `flat` if engagement < 0.35, `bright` if > 0.75, else `calm`. The mood word is passed to call 1 as a fact for the wording (`ai/calls/c01_child_voice.py:39`). The avatar's expression comes from `expression_for` in `services/api/sprites/expression.py` (a table over speaking, intent, correctness, engagement < 0.35, strength ≥ 0.66, quiet, shy). **No AI picks it** (stated in the module and in `services/practice/faces.py`).

### 2.8 Learning over a session

- A child "gets it" only as `strength` falling to 0 through moves; she then answers right every time. Engagement does not change the answer rule: it only changes who is more likely to speak (weights `engagement + 0.05`, `:437,497`) and the mood word.
- The session ends when every child with an error has answered right twice in a row (`finish_streak` 2, `:292-305`) or at 40 turns.
- **Memory:** within a session a child keeps `last_answer`, `streak` and `quiet_turns`. **Nothing carries across sessions or days**: the session lives in a server-side dictionary with a 2-hour life (`services/api/practice.py:62-64`), and her transcript stays on her phone.

### 2.9 Determinism (script run, printed)

A fixed class (seed 5, SUB-SFL, no counts) and a fixed script of 12 teacher moves (`pose_problem` to Ravi, `ask_explain`, `show_bundles`, `exchange_ten`, `pose_problem` to Meena, `check_back`, `scold` Arun, `praise`, `pose_problem` to Arun, `show_bundles` to Arun, `pose_problem` to the class, `other`). Config: start_strength 0.9, start_engagement 0.6, overhear 0.5, chorus_max 3, quiet_turns 2, max_turns 40, finish_streak 2.

Seed 5 (each child shown as `strength/engagement/streak/quiet`; Asha is the correct child):

```text
 1 pose_problem  to Ravi   -> Ravi   answer    ans=37 ok=False code=SUB-SFL chorus=['Asha'] | Ash:0.00/0.60/s1/q0 Rav:0.90/0.60/s0/q0 Mee:0.90/0.60/s0/q0 Aru:0.90/0.60/s0/q0 Pri:0.90/0.60/s0/q0
 2 ask_explain   to Ravi   -> Ravi   explain   ans=37 ok=False code=SUB-SFL chorus=['Arun', 'Meena'] | Ash:0.00/0.62/s1/q0 Rav:0.70/0.65/s0/q0 Mee:0.80/0.62/s0/q0 Aru:0.80/0.62/s0/q0 Pri:0.80/0.62/s0/q0
 3 show_bundles  to None   -> Asha   work_aloud ans=23 ok=True code=- chorus=['Arun', 'Meena'] | Ash:0.00/0.72/s2/q0 Rav:0.40/0.75/s0/q0 Mee:0.50/0.72/s0/q0 Aru:0.50/0.72/s0/q0 Pri:0.50/0.72/s0/q0
 4 exchange_ten  to Ravi   -> Ravi   work_aloud ans=23 ok=True code=- chorus=['Asha', 'Meena'] | Ash:0.00/0.78/s2/q0 Rav:0.10/0.85/s1/q0 Mee:0.35/0.78/s0/q0 Aru:0.35/0.78/s0/q0 Pri:0.35/0.78/s0/q0
 5 pose_problem  to Meena  -> Meena  answer    ans=1  ok=False code=SUB-SFL chorus=[] | Ash:0.00/0.78/s2/q0 Rav:0.10/0.85/s1/q0 Mee:0.35/0.78/s0/q0 Aru:0.35/0.78/s0/q0 Pri:0.35/0.78/s0/q0
 6 check_back    to Meena  -> Meena  doubt     ans=1  ok=False code=SUB-SFL chorus=['Ravi', 'Arun'] | Ash:0.00/0.80/s2/q0 Rav:0.00/0.88/s2/q0 Mee:0.15/0.82/s0/q0 Aru:0.25/0.80/s1/q0 Pri:0.25/0.80/s0/q0
 7 scold         to Arun   -> Arun   quiet     ans=None ok=None code=- chorus=[] | Ash:0.00/0.65/s2/q0 Rav:0.00/0.72/s2/q0 Mee:0.15/0.68/s0/q0 Aru:0.25/0.50/s1/q2 Pri:0.25/0.65/s0/q0
 8 praise        to None   -> Asha   thanks    ans=None ok=None code=- chorus=['Meena', 'Ravi'] | Ash:0.00/0.80/s2/q0 Rav:0.00/0.88/s2/q0 Mee:0.15/0.82/s0/q0 Aru:0.25/0.65/s1/q1 Pri:0.25/0.80/s0/q0
 9 pose_problem  to Arun   -> Arun   quiet     ans=None ok=None code=- chorus=[] | Ash:0.00/0.80/s2/q0 Rav:0.00/0.88/s2/q0 Mee:0.15/0.82/s0/q0 Aru:0.25/0.65/s1/q0 Pri:0.25/0.80/s0/q0
10 show_bundles  to Arun   -> Arun   work_aloud ans=24 ok=True code=- chorus=['Meena', 'Ravi'] | Ash:0.00/0.85/s2/q0 Rav:0.00/0.93/s3/q0 Mee:0.00/0.88/s1/q0 Aru:0.00/0.75/s2/q0 Pri:0.10/0.85/s0/q0
11 pose_problem  to None   -> Ravi   answer    ans=37 ok=True code=- chorus=['Asha'] | Ash:0.00/0.85/s3/q0 Rav:0.00/0.93/s4/q0 Mee:0.00/0.88/s1/q0 Aru:0.00/0.75/s2/q0 Pri:0.10/0.85/s0/q0
12 other         to None   -> Arun   confused  ans=None ok=None code=- chorus=['Asha', 'Meena'] | Ash:0.00/0.85/s3/q0 Rav:0.00/0.93/s4/q0 Mee:0.00/0.88/s1/q0 Aru:0.00/0.75/s2/q0 Pri:0.10/0.85/s0/q0
run 2 identical to run 1: True
seed 6 identical to seed 5: False
```

Reading it: **two runs with the same seed are identical, and seed 6 differs** (different speakers, answers and streaks: for example turn 3 Ravi speaks under seed 6 and Asha under seed 5, and turn 5 Meena answers 28, right, under seed 6 and 1, wrong, under seed 5). Note that the **strength and engagement columns are the same under every seed**: they follow only from the moves. The seed changes who speaks and whether each answer is right or wrong. Turn 1 shows a child answering wrong at strength 0.9 and turn 9 shows the scolded Arun answering nothing; turn 10 shows `show_bundles` taking a child from 0.25 to 0.00.

### 2.10 Sensitivity (script run, 200 seeds)

Protocol: the same class, then each teacher "round" is `pose_problem` to child X followed by one chosen move to child X, going round the four children with an error (the shy child only speaks when named), until the session finishes or 40 turns. Metric per move: mean turns to finish. 200 seeds per cell; 30 variants, each changing one constant (or one move's strength) by about 20 percent.

Baseline:

```text
  decomposition         13.6 turns   effect -0.30
  exchange_ten          13.6         -0.30
  show_bundles          13.6         -0.30
  compensation          14.6         -0.25
  ask_explain           22.2         -0.20
  check_back            22.2         -0.20
  order_probe           22.2         -0.20
  tell_rule             39.8 (cap)   -0.05
  repeat_rule_louder    40.0 (cap)   -0.02
```

Findings:

- **The ranking is the ranking of the numbers in the move list**, in tiers: three moves at −0.30 are *tied* (identical results), then −0.25, then three at −0.20 (tied), then the two weak ones that almost never finish a session. The simulator cannot tell `show_bundles` from `exchange_ten` or `decomposition`.
- **Changing the starting strength (0.72 or 1.0), the starting engagement (0.48 or 0.72), or `overhear` (0.4 or 0.6) never changes the order** of the nine moves (6 of 6 variants).
- **Scaling every move's strength by 0.8 or 1.2 never changes the order** (2 of 2). Scaling only the two weak moves, or only a tier, changes it only when it crosses the next tier: for example the three −0.30 moves at ×0.8 (−0.24) put `compensation` (−0.25) first.
- **Changing one move's own number by 20 percent re-orders it among its neighbours** (11 of the 30 variants change the full order, all from single-move edits or a tier crossing; the ties make the "order" partly an alphabetical tie-break, so read the *top tier* rather than the full order). In 25 of 30 variants the top tier still contains `decomposition`, `exchange_ten` and `show_bundles`.
- **Meaning for the mentor's question:** the model is only as good as the effect sizes Seema sets in the move lists (`TODO-HUMAN(Seema)` in each file: "review the moves, wording and effect values"). The simulator does not *discover* which move is best; it replays them.

### 2.11 Tests

- `tests/engine/test_simulator.py`, `test_simulator_stages.py`, `test_simulator_chorus.py`, `tests/practice/test_session.py`, `test_recorded_session.py`, `test_chorus_session.py`, `test_faces.py`, `test_content.py`, `test_calls_1_2.py`, `test_call_3.py`: **183 passed, 0 failed** (3 unrelated warnings).
- `python -m evals.runners.sim_fidelity --no-write --yes` (the offline `engine_templates` mode): **200/200 turns match (100%, bar 100%), PASS**. It asserts that on 200 scripted turns (4 errors × 5 seeds × 10 turns) the planned answer is the correct one or a wrong answer an independent oracle gives for that error, and that every number in the child's line is in the plan's allowed set. The live-model version recorded 60/60 on 17 Oct (`evals/results.md`, not re-run here: it needs the API).
- **What these do not test:** whether the simulated child *resembles* real children (Eval 3, "simulator realism", is `pending` human ratings), or whether the labeller reads moves correctly (Eval 4, `pending` Seema's labels).

## Step 3. Is anything Bayesian in the code?

No design document for a Bayesian model exists in the repository (`MODEL.md` and any similarly named file: not found). The checklist below is the one in the task prompt; the only place the repository mentions the idea is one build prompt (`docs/build/Claude Code prompt the end-to-end demo flow (Demo Studio).md:48`) and the reports that record it as not built (`docs/build/reports/STACK.md:52,53,146,147`).

| Element of the design | Status | Evidence |
| --- | --- | --- |
| Hidden variables for place value, the exchange idea, the written borrowing step, and a wrong habit | **Not found** | No such fields in `Child` (`engine/simulator.py:224`). The nearest things are one `error` code and one `strength` per child |
| A state space of 32 combinations (2 × 2 × 2 × 4) | **Not found** | No enumeration of states; no "32" anywhere in code or content |
| A response model: a probability table mapping state and item to an answer | **Not found** | The answer rule is `random() < strength` then a bug function (`simulator.py:345-347`). The only "table" is `SPOKE` in `services/api/sprites/expression.py`, which maps state to a *face*, not an answer |
| Teaching transitions by a logistic function of coverage, fit, scaffolding, attention and overload | **Not found** | Transitions are fixed additive steps from the move list (`plan_turn :413-428`); no logistic, no coverage, fit, scaffolding or overload |
| Attention dynamics (a low-pass filter with a time constant) | **Not found** | No attention variable. `engagement` moves by fixed steps and only affects who speaks and the mood word |
| Memory: a forgetting curve, and priming after a demonstration | **Not found** | Nothing decays between turns; no priming. State is lost when the session ends |
| A belief engine: a probability for each state, updated by Bayes' rule from answers | **Not found** | No belief over states; nothing is updated from answers. (The *diagnosis* of real sheets uses the 2-item rule, `CLAUDE.md` section 5, which is a count rule, not Bayes) |
| Choosing the next question by expected information gain | **Not found** | Problems come in the scenario's order or the problem she posed (`simulator.py:397-402`) |
| Soft evidence from a teacher's note | **Not found** | A teacher's note on feedback only picks her next lesson by code (`services/cohort_run/next_lesson.py`); it is not evidence in any model |
| Parameter uncertainty bands | **Not found** | All constants are single numbers in YAML. The sensitivity run above is a one-off script, not part of the product |
| Golden tests G1 to G7, and an independent oracle script that checks them | **Not found** (a different, real oracle exists) | `evals/runners/sim_fidelity.py:49` and `engine_items.py:47` are independent oracles for the *bug functions*, and `docs/design/pilot_forms.golden.json` is golden data for the answer keys. Neither is G1 to G7 |
| Behaviour tests B1 to B8 over many seeds | **Not found** (nearest built) | `tests/engine/test_simulator.py::test_wrong_rate_tracks_strength` (many draws) and the 200-turn fidelity eval check behaviour over seeds; they are not B1 to B8 |
| Exemplar replay on the same class and seed | **Built, partly** | Same seed and script replay exactly (`test_same_seed_same_session_different_seed_may_differ`, `test_the_chorus_is_replayable_from_the_seed`) and Watch runs replay recorded teacher styles (`content/demo_runs/`, `services/practice/watch.py`). It is replay of recorded sessions, not a model's exemplar comparison |

**Everything else called "child model" in the code is:**

- the Practice Class simulator (`engine/simulator.py`), described above; and
- the simulated block and the demo class (`data/synthetic/block.py`, `services/demo/scenario.py`): each child has a hidden **set of error codes** drawn from planted counts (`_draw_child :99`, `scenario.py:84-93`), and each answer is `error_answer_rate` 0.85 the error's wrong answer, else a 0.07 chance of a one-off slip (`_answer :138-152`, `data/synthetic/config.yaml:25-29`), else right. This is seeded random sampling, not Bayesian inference, and it is not the Practice Class's child.

**The verdict statistics** (`engine/evaluation.py`) are classical and unrelated to a child model: block scale = difference in change between track and comparison classes with a **95% percentile bootstrap over classes** (`:100-140`, uses `numpy`); pilot scale = **exact two-sided McNemar** on the discordant pairs (`mcnemar_exact :193`; 12 vs 2 gives p = 0.0129) plus an "extra fall" threshold (`pilot_extra_fall :212`, `pilot_verdict :234`). There is no prior, posterior or credible interval anywhere. They must not be described as Bayesian.

## Step 4. Where our claims may be wrong

Searched `docs/submission/*`, `docs/RUBRIC_MAP.md`, `AI_USAGE.md`, `README.md`, `docs/help/*.md`, `docs/practice-class.md`, `docs/engine.md`, `docs/design/*`, `strings/en.json`, `content/` and the assistant's reference for Bayesian, belief, hidden state, 32, probability table, hand-specified, "learning by chance", and for claims that a child "learns", "has attention" or "forgets".

**No document or screen claims a Bayesian model, a belief engine, attention or forgetting.** The only "Bayesian" hits are in prompts and the status report, all marked as planned. The claims that mention the simulated child:

| Where | Claim | Supported? | Corrected wording, if needed |
| --- | --- | --- | --- |
| `README.md:49`, `docs/RUBRIC_MAP.md` I1.1, `AI_USAGE.md:14,25` | Five simulated children who make her class's mistakes; the engine decides each answer and the model only says it | **Mostly.** True for who answers wrong and with what number. But call 2 (AI) decides what the teacher's move *means*, and the model chooses the words of the first speaker when `PRACTICE_AI_INTENTS=all` | "The engine decides every answer and number; the model puts them into words and reads which move she made (the move reader is not yet rated)" |
| `docs/design/cohort-coach-design.md:253`, `docs/practice-class.md:130`, `CLAUDE.md` section 5 | Wrong with probability = error strength; the wrong number comes from the bug function | **Yes** (`simulator.py:345-347`) | none |
| QA requirement list item 9 ("five simulated children at different levels, seeded and rule-based") | "different levels" | **Not as built.** All erring children start at strength 0.9; they differ by error, stage and shyness. The `mixed_level` flag in `CLAUDE.md` section 5 is not implemented | "five simulated children with different mistakes and ways of going wrong" |
| `CLAUDE.md` section 5, "Mixed-level persona. Scenario flag `mixed_level`" | exists, off by default | **No code** (`grep mixed_level` finds nothing) | Mark "planned, not built" |
| `docs/submission/deck.md:29`, `slides.md:30`, `README.md:8` | Rehearsal with simulated children is a hypothesis the pilot tests | **Yes**, and the code agrees: no claim that it works | none |
| `CLAUDE.md` section 5, "Move effects: show with bundles −0.3, ask to explain −0.2, check by adding back −0.2, just tell the rule −0.05, praise → engagement up, scold → engagement down and the child goes quiet" | the table | **Yes**, matches the move lists | none |
| `README.md` Practice Class row: "text turn median latency is over target (4968 ms against 3000 ms)" | | Yes, `evals/results.md` (17 Oct run, before the speed switches) | note the date |

**Where the code is stronger than the claim:**

- **Four stages of breakdown** change how a child errs (reversed writing, the other operation, no method yet). The decks describe this for diagnosis but not as part of the simulated child.
- **Overhear and chorus:** a move reaches the whole room at half strength, and up to three children speak a turn. Not in the deck.
- **Determinism and replay:** a session replays exactly from its seed (tested), and the first speaker is unchanged by the chorus (tested).
- **Fidelity eval:** every number a child says is checked against an independent oracle, 200 of 200 offline and 60 of 60 live.

**Where the claim is weaker than it sounds, and worth saying plainly:** the simulated child's improvement is a fixed countdown. It does not model understanding, attention, forgetting or transfer, and two different good moves with the same number are indistinguishable.

## Step 5. A true description for the deck and the video

**1. The simulated child, about 150 words**

> Each Practice Class has five made-up children, chosen to match the mistakes in her own class. One child is always right. The others each make one of her class's mistakes, and one is shy and speaks only when she calls her name. When she asks a question, a simple program, not the AI, decides who answers and whether the answer is right: a child who still has the mistake gives the wrong answer a rule can work out, such as 37 for 52 minus 29. Each time she does something that helps, such as showing bundles of ten, the children get a little less likely to make the mistake. A scolding makes a child go quiet. When every child has answered right twice in a row, or after 40 turns, the practice ends. The AI only puts the program's chosen answer into a child's words and reads what she did; it never decides an answer. The same seed always plays out the same way.

**2. What a Bayesian model would add, in one paragraph**

A Bayesian child model would give each simulated child a hidden state, for example whether she understands place value, the exchange of a ten, and the written borrowing step, and a belief over those states that is updated as she answers, so a child could understand some things and not others, and the same move could help one child and not another depending on what she already knows and how much attention she has. Today the child has a single number, an error strength that each move reduces by a fixed amount, so it cannot represent partial understanding, forgetting, or why a move works. It is not built, and nothing in the repository describes it beyond one build prompt. To build and validate it we would need a written specification and educator review of every state and transition; a sensitivity analysis showing which parameters change which conclusions (the run above shows the current ranking depends only on the move list's numbers); tests of its behaviour across many seeds and golden cases checked by an independent oracle; comparison with real classrooms and with teachers' judgments of whether the children "feel like my class" (the pending realism and pilot observation data); and a separate evaluation of the move labeller, because any child model is only as good as its reading of what the teacher did, and that reading (call 2) has not been rated yet.

## Open questions the code could not settle

1. **Which document defines "the Bayesian model"?** None is in the repository. If a design exists elsewhere (a doc outside the repo, a slide), its elements could not be checked beyond the table above.
2. **How good is the move labeller?** Eval 4 (agreement with Seema's labels, bar 85 percent) is `pending`, so the whole simulator's responsiveness rests on an unrated AI step. The offline fallback when call 2 fails is "other", which changes nothing (children do not improve).
3. **Are the effect sizes right?** The move lists say "first draft by the build" and ask Seema to review the values; no evidence ties −0.30 or −0.20 to real children.
4. **Does the simulated class resemble a real one?** Eval 3 (realism, human ratings) is `pending`.
5. **Should `PRACTICE_AI_INTENTS` stay `all`?** The README's "the model only says it" holds in both settings; only the amount of AI-written wording differs.
6. **`mixed_level`:** keep in `CLAUDE.md` as planned, or implement?

## Files

No file other than this report was created or changed by this check. Scratch scripts: a determinism run and a sensitivity run, kept outside the repository (the printed output is above). `git status --short` was captured before and after the investigation and compared: unchanged except for this report.
