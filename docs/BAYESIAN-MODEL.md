# The Bayesian child model (Practice Class, behind `SIMULATOR_MODEL`)

The written specification for the second child model of the Practice Class simulator. The default is still the rule-based model (`legacy`), and nothing here changes it. Code: `engine/child_model.py` (both models and the switch), `engine/simulator.py` (where they plug in). Built on 1 Nov 2026 from `docs/build/BAYESIAN-MODEL-BUILD-PROMPT.md`, following the read-only check in `docs/build/reports/BAYESIAN-CHECK.md`.

**What this is not.** It hasn't been checked against real children. Its parameters are chosen defaults, not fitted to data. It is a different way to simulate how five fictional children respond to a move, and nothing more.

## 1. The switch

| `SIMULATOR_MODEL` | Model |
| --- | --- |
| unset, empty or `legacy` | Rule-based (the default). Unchanged, turn for turn: the saved legacy runs replay exactly (`tests/engine/test_simulator_golden.py`) |
| `bayesian` | The model below |
| anything else | The API refuses to start (`services/api/main.py` calls `model_from_env`), with the message "SIMULATOR_MODEL must be legacy or bayesian (or unset for legacy)" |

One factory, `engine.child_model.model_from_env`, picks the model when a session is created (`engine.simulator.new_session`). The session stores it in `SessionState.model`, so changing the environment cannot switch a running session. Both models expose the same three steps to the simulator: `check` (the scenario), `start` (a child) and `learn` (from a move). Nothing else in the engine knows which model is running.

## 2. What stays exactly the same in both models

Who speaks, the answer test `rng.random() < strength`, the wrong number from the bug function, the four stages, engagement, going quiet after a scold, quiet turns, the overhear share, the chorus, the mood word, the faces, and the end of a session (every child with the error right twice in a row, or 40 turns). The per-turn generator `Random(f"{seed}:{turn}")` and the chorus generator `Random(f"{seed}:{turn}:chorus")` are used as before. The Bayesian model draws its prior and responsiveness from generators of its own. The per-turn generator makes the same number of `random()` calls under both models (`test_the_turn_generator_makes_the_same_draws_under_both_models`).

## 3. The model

**Latent state.** Each child with an error has one hidden binary state, L = "has repaired the misconception". The model holds a belief b = P(L = 1). The always-correct child has no belief: her strength is 0 and she is always right.

**Prior (individual differences).** When the seats are filled, each child with an error draws

- b0 ~ Beta(a, c), with a = K × (1 − start_strength) and c = K × start_strength, so the mean of b0 is 1 − start_strength (0.10 for every scenario today). Drawn from `random.Random(f"bayes-prior:{seed}:{seat}")`.
- a responsiveness r = RESPONSIVENESS_SCALE × Beta(RESPONSIVENESS_SHAPE, RESPONSIVENESS_SHAPE), mean 1, range 0 to 2. Drawn from `random.Random(f"bayes-resp:{seed}:{seat}")`.

**Move → chance it teaches.** A move with legacy effect e on strength teaches with probability

T = LEARN_CAP × min(1, |e| / S)

where S = EFFECT_SCALE (default: the largest |e| in the scenario's move list). The ranking of moves comes only from the move-list numbers. Equal effects give equal T, so tied moves stay tied. A move that would raise strength makes session creation fail under this model (`check`), because the model has no forgetting.

**Update.** If the move reaches her directly:

b ← b + (1 − b) × min(1, T × r)

If she only overheard it (a move aimed at another named child), the gain is OVERHEAR × (1 − b) × min(1, T × r). OVERHEAR is the same scenario value legacy uses (0.5). The cap on T × r applies before the halving, so an overheard move always gives exactly half the direct gain from the same state. As in legacy, only children with an error learn, and only from a move with a non-zero effect. A scold makes only the child reached go quiet and teaches nothing.

**Derived strength (the interface).** Everything that reads `child.strength` (the answer test, stages, the mood, the faces, the confusion meter) reads

strength = P(wrong) = (1 − b) × (1 − GUESS) + b × SLIP

With the defaults, a child who certainly still holds the mistake is wrong 95 times in 100, and one who has certainly repaired it is wrong 5 times in 100. Under legacy the range is 0 to 1.

**State.** `Child` gains `belief`, `responsiveness` and `last_gain` (all None under legacy). `engine.simulator.state_to_dict` and `state_from_dict` turn a session state into plain JSON-ready data and back. The server's session store is unchanged: an in-memory dictionary, 2-hour life.

**Trace.** In Bayesian mode each `TurnPlan` carries `trace`, one row per child with an error: belief, r, the T applied, direct or overhear, the gain, the derived strength, the stage, and the answer drawn that turn. It goes to the debug log in `services/practice/session.py` and is never in the API response (`test_legacy_turns_carry_no_trace_and_bayesian_trace_is_not_in_the_api_response`).

## 4. Parameters

All are code defaults in `engine.child_model.BayesParams`, overridable from `.env` (listed in `.env.example`). A bad value stops the API at startup.

| Constant | `.env` | Default | Meaning |
| --- | --- | --- | --- |
| PRIOR_CONCENTRATION (K) | `BAYES_PRIOR_CONCENTRATION` | 20 | How tightly starting beliefs sit around their mean |
| RESPONSIVENESS_SCALE | `BAYES_RESPONSIVENESS_SCALE` | 2.0 | r = scale × Beta(shape, shape) |
| RESPONSIVENESS_SHAPE | `BAYES_RESPONSIVENESS_SHAPE` | 4 | |
| LEARN_CAP | `BAYES_LEARN_CAP` | 0.6 | T for the strongest move |
| EFFECT_SCALE (S) | `BAYES_EFFECT_SCALE` | the largest \|effect\| in the move list (0.30 today) | |
| GUESS | `BAYES_GUESS` | 0.05 | P(right) while the misconception holds |
| SLIP | `BAYES_SLIP` | 0.05 | P(wrong) once it is repaired |

The `.env` names carry a `BAYES_` prefix so that generic names such as `GUESS` and `SLIP` cannot clash with other settings.

## 5. Move effect → T, with today's move lists

Checked by `test_the_move_effect_to_learning_probability_table` (SUB-SFL). S = 0.30, LEARN_CAP = 0.6.

| Effect e | T | Moves (SUB-SFL list) |
| --- | --- | --- |
| −0.30 | 0.60 | show_bundles, exchange_ten, decomposition (tied) |
| −0.25 | 0.50 | compensation |
| −0.20 | 0.40 | ask_explain, check_back, order_probe (tied) |
| −0.05 | 0.10 | tell_rule |
| −0.02 | 0.04 | repeat_rule_louder |
| 0 | 0 | pose_problem, praise, scold, give_the_answer, other, off_task |

The other move lists use the same effect values, with regroup_ten (ADD-NOCARRY) and show_chart (PV-HEARD) at −0.30.

## 6. What is and is not Bayesian here

- **Bayesian in structure:** a latent binary state with a probability over it, guess and slip emission probabilities (the knowledge-tracing form), and Beta priors that give each child her own starting belief and responsiveness.
- **Not a posterior update from answers:** the belief moves only with the teacher's moves. A child's answers are drawn from the derived strength and don't feed back into her belief. Classic knowledge tracing updates a *tutor's estimate* by Bayes' rule after each answer. Here the belief is the simulated child's own state.
- **Unrelated to the verdicts:** the impact statistics stay classical, a bootstrap over classes at block scale and an exact McNemar test at pilot scale (`engine/evaluation.py`). Nothing in them is Bayesian.

## 7. Evidence

- Tests: `tests/engine/test_child_model_bayes.py` (determinism, ranges, prior and responsiveness differences, the T table, monotonic gains, tied moves, the overhear half, scold, chorus, stages, bug-function answers, end of session, the correct child, the draw count, calibration, the switch, serialising, the trace) and `tests/engine/test_simulator_golden.py` (legacy turn for turn against `tests/fixtures/sim_legacy_golden.json`, saved by `scripts/capture_sim_golden.py` before any engine change).
- Calibration: over 400 simulated sessions with random moves, the share of right answers in each P(correct) bucket with at least 200 draws must be within 0.05 of the bucket's mean predicted P(correct) (`test_calibration_the_derived_p_correct_matches_the_drawn_answers`).
- Comparison of the two models on the BAYESIAN-CHECK 2.10 drill: `evals/results/sim_model_compare.md` (generated by `python -m evals.runners.sim_model_compare`). Its legacy table reproduces the check's baseline.
- Simulator fidelity (`python -m evals.runners.sim_fidelity --no-write --yes`) passes in both modes. It checks that every number a child says is the engine's. It doesn't measure realism.

## 8. Known limits

- The parameters are chosen defaults, not fitted to real children.
- The move effect numbers (and so T) haven't been reviewed by Seema (`TODO-HUMAN(Seema)` in each move list).
- The move reader (call 2) that turns her words into a move is unrated: Eval 4 is pending. Either model is only as good as that reading.
- Realism (Eval 3, human ratings) is pending for both models.
- `mixed_level` isn't implemented.
- It isn't one hidden variable per concept. There is no place-value, exchange or borrowing state space, no attention, no forgetting, and no question choice by information gain.
- Tied moves stay tied: the model can't tell show_bundles from exchange_ten, because their effects are equal in the move list.
- In Bayesian mode, some existing tests that pin legacy numbers (a start strength of exactly 0.9, exact −0.3 steps, strength 1 always wrong) and the recorded-rehearsal replays (recorded AI fixtures keyed on legacy answers) fail by design. They pass under the default and under `legacy`, which is what the build requires.
