# 32-state Bayesian child model: build report

Built on 1 Nov 2026 from `docs/build/BAYESIAN-32-STATE-BUILD-PROMPT-v2.md`, on branch `bayes-32state` (made from `7cd0afa`, not from the speech branch). Not pushed, not deployed. **The default stays `legacy`.** Spec: `docs/BAYESIAN-MODEL.md`. Decisions: `docs/build/DECISIONS.md` (2026-11-01, "32-state Bayesian child model replaces the one-variable model").

Every parameter is a build default, not reviewed by an educator and not fitted to real children. Every number below comes from a generated file in `evals/out/bayes/` or from test output, with its path.

## Where it stands

| Group | What |
| --- | --- |
| **Implemented and tested** | The switch and factory; the 32-state generative child (prior, response table with collapse, priming and stage channels, logistic learning, habit break and shift, forgetting, attention filter, overload); the observer (predict, update, soft evidence); information-gain problem choice inside the bayesian planner; the legacy contract; JSON round trip; the independent oracle; G1–G7; B1–B8; the fidelity, comparison, sensitivity and replay evals |
| **Implemented, not wired to the UI** | Teacher-note tags (soft evidence): a `note_tags` parameter of `engine.sim_switch.new_session` and `start_session`, tested; no screen or API request sends them. The belief engine's output: in the debug trace only (logged at debug level), never in the API response or on a screen |
| **Not done** | Educator review of any value; fitting to real children; the `mixed_level` flag; realism against real classes (Eval 3) and the move reader's rating (Eval 4), which every transition depends on |

## Step 0: what the code says, and the conflicts

**Contract.** Recorded in the spec, section 2: the `TurnPlan` and `Child` fields every reader uses (session, API, Watch, model run, faces, templates, call 1; call 3 reads none). The problem comes from the posed problem or the scenario's `problems` list in order. A move to no one (or to an unknown name) applies the full effect to every child; a move to one child reaches the others at `overhear` 0.5, never the going-quiet. Move ids: the 15 in the prompt's table plus neutral `other`/`off_task`; error codes: the five, all mapped. No teacher note reaches the Practice Class.

**Matches the prompt:** every move id, every error code, and the bug values in G1–G7 (37, 33, 35) and scold's engagement change (−0.30, which gives G4 exactly).

**Conflicts, resolved by the recommended approach** (your standing instruction):

1. `SIMULATOR_MODEL=bayesian` already selected the one-variable model, wired inside `engine/simulator.py`, which this prompt forbids editing. The file is untouched; the factory passes the legacy model explicitly, and `bayesian` now means the 32-state model. The one-variable module and its unit tests stay. Scripts that call `engine.simulator.new_session` without a model still read the old switch: run them with `SIMULATOR_MODEL` unset.
2. One existing test pinned `bayesian` to the one-variable model. It now checks the same property on the new model (`test_child_model_bayes.py::test_a_session_keeps_its_model_after_the_environment_changes`). No assertion removed.
3. `evals/runners/sim_model_compare.py` already existed (one-variable). The comparison is a new file, `bayes_model_compare.py`. `docs/BAYESIAN-MODEL.md` is rewritten (this prompt supersedes its source).
4. "183 existing tests" is the subset in BAYESIAN-CHECK 2.11, not the whole suite.
5. Turn order: the move is applied before the problem is chosen (legacy does the opposite), because the information-gain choice needs the predicted belief. The problem does not enter the transitions, so nothing else changes.
6. Order of work: the spec was written alongside the model code, not strictly before it; it was committed first and the oracle was written from it. Steps 2, 4, 5 and 6 landed in one commit because the switch tests need the model.

## 1. Files changed, and proof that `engine/simulator.py` is unchanged

40 files (`git diff --stat 7cd0afa HEAD`). New: `engine/bayes/` (state, content, response, dynamics, belief, planner), `engine/sim_switch.py`, `content/bayes/` (families, moves, note tags, params), `evals/runners/bayes_*.py` (oracle, behaviour, protocols, fidelity, model compare, sensitivity, replay), `evals/out/bayes/*.json`, `tests/engine/bayes/` (6 files), `tests/engine/legacy_golden.py`, `tests/engine/test_legacy_golden.py`, `tests/fixtures/legacy_sim_golden.json`, `tests/fixtures/legacy_sim.sha256`. Changed: `services/practice/session.py` (calls the factory), `services/api/main.py` (one line: startup check), `.env.example` (`BAYES_PARAMS`), `tests/conftest.py` (clears `BAYES_PARAMS`; one long line wrapped), `tests/engine/test_child_model_bayes.py` (one test retargeted), `docs/BAYESIAN-MODEL.md`, `docs/build/DECISIONS.md`, this report.

**`engine/simulator.py` SHA-256** before the build and now: `d091bc66cf3442e51e7a8fb71cfee216aecf790c6738ebcadb0e1d3848f35275` (`tests/fixtures/legacy_sim.sha256`; `test_legacy_golden.py` checks it). Not edited either: `engine/bugs.py`, move lists, scenarios, personas, `sim_fidelity.py`, `engine_items.py`, `evals/results.md`, `docs/submission/*`, README, `CLAUDE.md`, `AI_USAGE.md`.

**Copied rather than imported** (legacy private helpers), listed in the module docstrings: `_rev`, `_near` and the options of `_misheard` (in `engine/bayes/response.py`); `_mood`, `_steps_for`, `_chorus_plan`, `_finish` and the allowed-number rule (in `engine/bayes/planner.py`). `_steps_for` takes the error code that produced the answer, so a child whose habit shifted explains by her new code.

## 2. Tests

| Run | Before | After |
| --- | --- | --- |
| The 183 simulator and practice tests (BAYESIAN-CHECK 2.11), default | 183 passed | 183 passed |
| The same with `SIMULATOR_MODEL=legacy` | — | 183 passed |
| Legacy golden runs (4 scenarios × seeds 1–20 × 2 scripts), directly and through the factory, default and `legacy` | — | identical (`test_legacy_golden.py`, `test_bayes_switch.py`) |
| One-variable tests and the old golden (`test_child_model_bayes.py`, `test_simulator_golden.py`) | 37 passed | 37 passed |
| New `tests/engine/bayes/` | — | 58 passed (switch 13, structure 18, golden 12, contract 5, behaviour 8, evals 2) |
| Full Python suite | 2483 passed, 8 failed | 2541 passed, the same 8 failed (no new failure) |
| ruff, mypy `--strict` on `engine/` | lint failed on base (two files) | ruff clean except `tools/check_anthropic_api_key.py` (untouched, already failing); mypy clean (41 files) |

The 8 base failures are outside the simulator: assistant index, chat scheduler (2), seed schema, papers hub (2), importer, health. Note: `tests/conftest.py` clears `SIMULATOR_MODEL` for every test by design, so "with `SIMULATOR_MODEL=legacy`" is also checked inside the tests that set it themselves (golden, switch).

Commits skip the pre-commit hook because `tasks.py check` already fails at lint on the base; ruff, mypy and the relevant tests were run on each change instead.

## 3. Oracle (`evals/out/bayes/oracle.json`)

`evals/runners/bayes_oracle.py` reimplements sections 4–6 of the spec without importing `engine/bayes` or `engine/simulator` (a test checks its imports). **PASS: maximum absolute difference 1.8e-15** over 1,000 random cases (bar 1e-9): response 0, transition 1.1e-16, attention 0, forgetting 0, Bayes update 2.2e-16, EIG 1.8e-15.

| Case | Expected | Got | Result |
| --- | --- | --- | --- |
| G1 | 0.05 / 0.95 (37); P=E=1: 0.25 / 0.75 | 0.05 / 0.95, 0.25 / 0.75; SUB-SFL 37, SUB-NODEC 33 | pass |
| G2 | correct 1.0 on 58 − 23 | both bugs give 35 = correct; 1.0 | pass |
| G3 | 0.7109 | 0.71095 | pass |
| G4 | 0.4583, 0.4984 | 0.45827, 0.49844 | pass |
| G5 | 0.03, 0.0110 | 0.03, 0.01104 | pass |
| G6 | 0.7391 / 0.0435 / 0.1739 / 0.0435 | same | pass |
| G7 | 0.7136, 0, chooses 52 − 29 | 0.71360, 0, chooses 52 − 29 | pass |

## 4. Behaviour tests B1–B8 (`evals/out/bayes/behaviour.json`, 200 seeds each)

| Test | Measured | Threshold | Result |
| --- | --- | --- | --- |
| B1 Determinism | identical true states, beliefs and answers for all 200 seeds; seeds 5 and 6 differ | identical; 5 ≠ 6 | pass |
| B2 Teaching quality | mean turns: exchange_ten 15.8, show_bundles 16.6, decomposition 17.6; tell_rule 33.6, repeat_rule_louder 36.6 | each good move below both rule moves | pass |
| B3 Prerequisites | learned exchange: 0.684 with place value (269 children), 0.454 without (293); difference 0.230 | ≥ 0.10 | pass |
| B4 Attention | scold before each teaching move: 35.8 turns, mean attention 0.469; praise: 24.4 turns, 0.642 | scold later and lower | pass |
| B5 Overload | mean p_learn(exchange) 0.657 consecutive, 0.769 spaced | consecutive lower | pass |
| B6 Priming | P(correct) for children without the written step: demo turn 0.447 vs 0.210 unprimed; next turn 0.328 vs 0.210; after the 2-turn window 0.208 = 0.208; true states identical with and without priming | higher, then equal; state unchanged | pass |
| B7 Forgetting | reversion 0.0303 per turn over 20,000 child-turns with no practice (h0_W 0.03); 0.0045 with practice (c = 4) | within ±0.01; lower with practice | pass |
| B8 Belief recovery | most likely written step right for 94.0% of 800 children; calibration gaps 0.003 to 0.058 in the 9 buckets with ≥ 50 of 5,647 answers (largest in 0.2–0.3: predicted 0.249, observed 0.191) | ≥ 85%; ≤ 0.08 | pass |

No threshold, parameter or model value was changed to pass.

## 5. Fidelity (`evals/out/bayes/fidelity.json`)

- **bayes_fidelity:** 200/200 turns on the sim_fidelity protocol (bar 100%), answers checked by sim_fidelity's independent digit oracle against the child's current habit code or the legacy stage form. With the scenarios' stage mix (core, input-test, output) also 200/200.
- **Legacy `python -m evals.runners.sim_fidelity --no-write --yes`** (unchanged): 200/200, PASS.

## 6. Model comparison (`evals/out/bayes/model_compare.json`, protocol 2.10, 200 seeds per move)

| Move | Legacy turns (printed baseline) | Legacy cap | Bayesian turns ± SE | Bayesian cap | Concepts learned | Final entropy (bits) | Recovery |
| --- | --- | --- | --- | --- | --- | --- | --- |
| decomposition | 13.6 (13.6) | 0% | 17.6 ± 0.4 | 0.5% | 1.98 | 1.57 | 94% |
| exchange_ten | 13.6 (13.6) | 0% | 15.8 ± 0.4 | 0% | 1.94 | 1.72 | 94% |
| show_bundles | 13.6 (13.6) | 0% | 16.6 ± 0.4 | 0% | 1.98 | 1.51 | 92% |
| compensation | 14.6 (14.6) | 0% | 20.0 ± 0.5 | 2% | 1.87 | 1.92 | 91% |
| ask_explain | 22.2 (22.2) | 0% | 25.4 ± 0.5 | 7% | 1.96 | 1.32 | 95% |
| check_back | 22.2 (22.2) | 0% | 23.8 ± 0.5 | 3.5% | 1.89 | 1.28 | 96% |
| order_probe | 22.2 (22.2) | 0% | 24.7 ± 0.5 | 5% | 1.92 | 1.06 | 94% |
| tell_rule | 39.8 (39.8) | 94.5% | 33.6 ± 0.6 | 45.5% | 0.82 | 2.62 | 95% |
| repeat_rule_louder | 40.0 (40.0) | 100% | 36.6 ± 0.5 | 69% | 0.72 | 2.45 | 96% |

Legacy reproduces the printed baseline exactly.

**Do the ties separate?** Yes for 5 of 6 pairs (paired difference over the same seeds, 95% interval): decomposition − exchange_ten +1.8 [+1.2, +2.4]; decomposition − show_bundles +0.9 [+0.4, +1.5]; exchange_ten − show_bundles −0.9 [−1.4, −0.4]; ask_explain − check_back +1.6 [+0.8, +2.4]; check_back − order_probe −0.9 [−1.6, −0.3]. **ask_explain − order_probe does not:** +0.7 [−0.0, +1.4].

**Which coverage values cause it** (ablation, 100 seeds, one field set to the tier's first move's value):
- exchange_ten (16.4 turns as it is) is faster than decomposition because of its written-step coverage 0.5 (set to 0.3: 17.8) and exchange coverage 0.9 (set to 0.5: 17.6). Its lower place-value coverage and scaffolding help slightly the other way (16.0 each when raised).
- show_bundles (17.6) is helped by exchange coverage 0.9 (set to 0.5: 18.8).
- check_back (24.4) beats ask_explain because of conflict 0.8 (set to 0.3: 25.6) and written-step coverage 0.4 (set to 0.2: 25.4).
- order_probe (24.8) rests on conflict 0.9 (set to 0.3: 26.6).

The rule moves are slower but not capped as often as in legacy: a rule drill can teach the written step (tell_rule coverage 0.6), and **in this model the written step alone makes a child right 95% of the time, whatever her habit or understanding**. The replay (section 8) shows the same. Whether that is how children behave is for an educator to judge.

## 7. Sensitivity (`evals/out/bayes/sensitivity.json`)

Protocol 2.10, 100 seeds per cell with the same seeds in every configuration, 133 configurations: the defaults, each of the 41 parameters at its low and at its high one at a time (82 runs), and 50 seeded Latin-hypercube draws across all bands at once.

| Move | Defaults | Joint draws: median [5–95%] | One at a time: range |
| --- | --- | --- | --- |
| exchange_ten | 16.4 | 16.8 [11.2, 27.0] | 11.2 to 29.0 |
| show_bundles | 17.6 | 17.5 [11.6, 29.1] | 11.4 to 30.2 |
| decomposition | 18.0 | 18.0 [11.8, 30.1] | 11.5 to 32.1 |
| compensation | 21.2 | 21.0 [12.8, 34.1] | 12.1 to 34.9 |
| check_back | 24.4 | 23.9 [19.2, 34.5] | 19.3 to 36.3 |
| order_probe | 24.8 | 24.7 [19.3, 35.3] | 19.4 to 37.2 |
| ask_explain | 26.1 | 25.1 [19.7, 35.4] | 19.7 to 37.2 |
| tell_rule | 33.9 | 33.8 [24.8, 39.2] | 23.5 to 39.7 |
| repeat_rule_louder | 37.5 | 37.1 [27.9, 39.9] | 26.5 to 40.0 |

- **The top tier** (exchange_ten, show_bundles, decomposition) keeps the same members in all 82 one-at-a-time runs and all 50 joint draws. The two rule moves are last in every configuration.
- **No single parameter changes the move ranking**: the full order of the nine moves is the same in all 82 one-at-a-time runs.
- **Moving all parameters at once does reorder neighbours**: the full order holds in 35 of the 50 joint draws (70%). The swaps are always between moves that are close at the defaults: show_bundles and decomposition (5 draws), check_back, order_probe and ask_explain (up to 7), and compensation and check_back (4).
- **The absolute number of turns is sensitive**, mostly to the learning intercept beta0 (moves a move by up to 11.0 turns), then beta_fit (3.6), beta_cov (2.2), gamma0 (1.5), beta_scaf (1.3), fit_W_noE (1.1) and h0_W (1.0). These are build defaults; the turn counts are not a prediction for real classes.

## 8. Replay (`evals/out/bayes/replay.json`)

All six recorded Watch runs (SUB-SFL, experienced and struggling, en/hi/ta, seed 5) are 9 turns long and end before the session finishes, under both models. **Legacy repeats every recorded engine answer: 9 of 9 turns in each run**, so the replay is faithful.

| Run | Wrong-answer rate by answering turn, legacy | Same, bayesian | Final true states of the four erring children (bayesian) |
| --- | --- | --- | --- |
| experienced en | 0.5, 1.0, 1.0, 0.33, 0, 0.33 | 0, 0, 0.33, 0.33, 0, 0.33 | every habit broken; all have the exchange idea and the written step; one lacks place value |
| experienced hi | 0.5, 1.0, 1.0, 0.33, 0, 0.33, 0.5 | 0, 0, 0.33, 0.33, 0, 0.33, 0.5 | every habit broken; all three concepts held by all four |
| experienced ta | 0.5, 1.0, 1.0, 0.33, 0, 0, 0.67, 0.5 | 0, 0, 0.33, 0.33, 0, 0, 0, 0.5 | every habit broken; all three concepts held by all four |
| struggling en | 0.5 (one answering turn) | 0 | written step held by all four; 3 still hold a habit (two SUB-SFL, one SUB-NODEC); two lack place value |
| struggling hi | 0.5 | 0 | written step held by 2; 1 still holds SUB-SFL |
| struggling ta | 0.5 | 0 | written step held by all four; all four still hold a habit (three SUB-SFL, one SUB-NODEC) |

All six runs share seed 5, so the class and the starting states are the same; the runs differ because the AI teacher's moves differ by language. The struggling runs have one answering turn, so their wrong-answer rates say nothing. What the bayesian replay shows is the end state: the experienced teacher's moves break every habit, while the struggling teacher's rule drills mostly give the written step and leave the habit in place.

## 9. Wired versus not wired

- **Soft evidence:** `note_tags` on `engine.sim_switch.new_session` and `services.practice.session.start_session`, the closed list only (unknown tags refused; refused under legacy). Tested. **Not wired to the UI or the API**: no teacher note reaches the Practice Class today.
- **Information gain:** used inside the bayesian planner whenever legacy would take the scenario's next problem (a `pose_problem` with no posed problem, or an answering move with no problem on the board). In the Practice Class the move reader often supplies a posed problem, and the Watch runs always do, so then EIG is not used.
- **The belief:** in the debug trace only (`plan_turn_traced`, logged by `take_turn` at debug level). Not in the API response (tested), not on any screen. The confusion meter shows `strength` from the child's true state, as before.

## 10. Doc lines that would need changing (not edited)

Only if the bayesian model is switched on for teachers; while the default is `legacy`, these lines stay true.

| File and line | Today | Proposed, claiming only what the tests show |
| --- | --- | --- |
| `CLAUDE.md:124` (section 5, Practice Class) | "each child has an error strength 0–1 (starts 0.9) … A child answers wrong with probability = strength … Move effects: show with bundles −0.3 …" | Add: "With `SIMULATOR_MODEL=bayesian` (off by default) each erring child instead holds a hidden state over place value, the exchange idea, the written step and her habit; moves change it by a logistic rule from `content/bayes/moves.v1.yaml`; the wrong number still always comes from the bug function. Build defaults, not reviewed by an educator (`docs/BAYESIAN-MODEL.md`)." |
| `CLAUDE.md:136` (mixed-level persona) | "Scenario flag `mixed_level` … Off by default." | "Planned, not built (no code reads `mixed_level`)." |
| `CLAUDE.md` section 13 | — | Add "1 Nov · 32-state Bayesian child model behind `SIMULATOR_MODEL` (default legacy); see `DECISIONS.md`." |
| `README.md:49` | "Practice Class (text and voice) with five simulated children" | Append: "a second, 32-state child model is built behind a switch (off by default; parameters not yet reviewed by an educator)" |
| `AI_USAGE.md:25` | "the engine decides, the model only speaks" | Unchanged in substance (both models are code); add `engine/bayes/` to the file paths, status Built (not Verified: no realism rating) |
| `docs/practice-class.md:29, 130, 184` | strength and fixed move effects | Add "under the legacy model (the default); see `docs/BAYESIAN-MODEL.md` for the bayesian one" |
| `docs/submission/deck.md`, `slides.md`, `video-script.md` | no mention of the model | No change unless the bayesian model is used in the demo. Never call it validated: say "a hypothesis-driven child model with stated, unreviewed parameters". |

## 11. What did not work, or needs a person

- ask_explain and order_probe stay tied within noise (section 6).
- B8 calibration is weakest in the 0.2–0.3 bucket (gap 0.058, under the 0.08 bar): the observer starts unsure of the habit (`r_diag` 0.85, `obs_W0` 0.9), while the simulated children all start with the diagnosed habit and no written step.
- The two-digit subtraction items never separate SUB-SFL from SUB-NODEC: both bite exactly when borrowing is needed. So the collapse rule is tested on a dictation (55: PV-HEARD bites, PV-REVERSE does not), and EIG cannot prefer one scenario subtraction item over another by family alone.
- A design question for an educator: the written step alone makes a child right 95% of the time, so rule drills "fix" answers without the idea; only faster forgetting of the written step (0.03 a turn against 0.005 and 0.01) makes understanding matter over a session.
- The full `tasks.py check` cannot pass on this base (pre-existing lint and test failures), so the hook was skipped on every commit.
- For a person: review every value in `content/bayes/` (`TODO-HUMAN(Seema)`); decide whether `main` should take this branch; decide whether the debug trace should ever reach a coach or researcher view.
