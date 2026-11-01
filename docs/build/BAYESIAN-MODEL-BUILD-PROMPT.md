# Claude Code build prompt: Bayesian child model (behind SIMULATOR_MODEL)

Project: Cohort Coach, Practice Class simulated child
Default stays `legacy`. Nothing here is built until the tests and evals below pass.

---

## TASK

Build a Bayesian child model for the Cohort Coach Practice Class simulated child (engine/simulator.py), behind an .env switch. Default stays the current rule-based model, byte-for-byte unchanged. Touch only the simulator, its config, tests, a new eval script and docs. No changes to decks, existing evals, recorded results, or unrelated files.

## STEP 0: READ FIRST (no edits yet)

Read: BAYESIAN-CHECK.md (repo root or docs), engine/simulator.py (Child :224-234, SessionState :238-246, _clamp :273, fill_seats :640-695, _apportion :698, plan_turn :371-550 incl. move effect :413-428, answer rule :344-358, chorus :491, engagement weights :437,497, _mood :361-368, finish logic :292-305), content/movelists/*.yaml, content/scenarios/*.yaml, services/practice/session.py, services/api/practice.py (session dictionary), services/api/sprites/expression.py, the config/.env loading, tests/engine/test_simulator*.py, tests/practice/*, evals/runners/sim_fidelity.py.

Write a short summary using the repo's real names: where strength is stored, changed, read; where the RNG is created and how many draws each turn consumes. If anything contradicts this prompt, stop and list it before editing.

## LEGACY MODEL (must not change)

Strength starts at start_strength (0.9) for an erring child, 0 for the correct child. A move subtracts its fixed effect (erring children only, effect non-zero). Overhear applies 0.5 of the effect to non-targeted children. Wrong when rng.random() < strength; wrong number from the bug function. rng = Random(f"{seed}:{turn}"), chorus rng = Random(f"{seed}:{turn}:chorus"). Engagement, quiet, mood, stages, chorus selection, session end (2 right in a row or 40 turns) are not touched by this task.

## FIRST COMMIT: GOLDEN FIXTURES

Before any change, run legacy for a fixed grid (scenarios SUB-SFL and one other, seeds 1-20, a fixed 12-move script like the one in BAYESIAN-CHECK.md section 2.9 plus a script using every move in the list) and save per-turn speaker, answer, correctness, and every child's strength/engagement/streak/quiet as fixtures. Commit: "capture legacy simulator golden fixtures".

## BAYESIAN MODEL: Bayesian knowledge tracing with per-child uncertainty

Latent state per erring child: L = "has repaired the misconception". Belief b = P(L=1).

1. **Prior.** At seat filling, each erring child draws b0 ~ Beta(a, c) with a = K * (1 - start_strength) and c = K * start_strength, so the mean of b0 is 1 - start_strength (0.10). K = PRIOR_CONCENTRATION (default 20). Draw from a dedicated RNG: random.Random(f"bayes-prior:{seed}:{seat}"). Never use the per-turn RNG for priors.
2. **Responsiveness.** Each erring child draws r = RESPONSIVENESS_SCALE * Beta(ar, ar) from random.Random(f"bayes-resp:{seed}:{seat}"), defaults ar=4, scale=2.0 (mean 1.0, range 0-2). Config constants.
3. **Move to learn probability.** For a move with legacy effect e on strength: T = LEARN_CAP * min(1, |e| / S), S = EFFECT_SCALE (default 0.30 = largest |effect| across the move lists; read it from the move lists at load time if not set), LEARN_CAP default 0.6. Result with current lists: -0.30 -> 0.60 (three tied), -0.25 -> 0.50, -0.20 -> 0.40 (three tied), -0.05 -> 0.10, -0.02 -> 0.04, 0 -> 0. Equal effects give equal T. The ranking depends only on the move-list numbers. No move has a positive effect today; if a positive effect is ever found, fail loudly at load (do not invent forgetting).
4. **Update.** Direct hit (the child reached): b <- b + (1 - b) * min(1, T * r). Overhear (non-targeted erring children): the gain uses 0.5 * T (OVERHEAR from the same config the legacy model uses), exactly half the direct gain from the same state. Same conditions as legacy: erring children only, only when the effect is non-zero. Scold/quiet, engagement, quiet_turns and streak logic stay as in legacy, in both modes.
5. **Derived strength (the interface to the rest of the engine).** strength = P(wrong) = (1 - b) * (1 - GUESS) + b * SLIP, defaults GUESS = 0.05, SLIP = 0.05. Everything that reads child.strength (answer test rng.random() < strength, stages, expression_for, mood, finish checks) reads this derived value. Do not add new RNG draws: the number of draws per turn must equal legacy. The wrong number still comes from the bug function unchanged. The correct child: strength 0, no belief state, always right, as in legacy.
6. **Stages:** unchanged logic, same probability test on the derived strength. mixed_level stays unimplemented; do not touch it.
7. **State.** Add belief, responsiveness, last_gain to Child (None in legacy mode). Make session state plain-dict serialisable. Do not change the session store (server dictionary, 2-hour life).
8. **Trace** (bayesian mode only, debug/log path only; not in the normal API response): per turn per erring child: belief, r, T applied, direct or overhear, derived strength, drawn outcome.

## THE SWITCH

- .env `SIMULATOR_MODEL = legacy | bayesian`. Unset = legacy. Any other value: fail at startup with a clear message.
- All new constants (PRIOR_CONCENTRATION, RESPONSIVENESS_SCALE, RESPONSIVENESS_SHAPE, LEARN_CAP, EFFECT_SCALE, GUESS, SLIP) in code defaults, overridable from .env, documented in .env.example with comments.
- One factory picks the model at session creation; the session records its model, so a mid-session env change cannot switch it. Both models expose the same interface so the rest of the engine is untouched.

## TESTS (add; never weaken or delete existing)

- All 183 existing tests pass with the default and with SIMULATOR_MODEL=legacy.
- Golden: legacy output for the committed fixtures is identical after the change.
- Bayesian determinism: same seed gives identical sessions; seed 6 differs from seed 5.
- Belief in [0,1]; derived strength in [0,1].
- Monotonic: stronger move gives gain >= weaker move from the same state; the three -0.30 moves give identical sessions for the same seed (same for the three -0.20 moves).
- Overhear gain is exactly half the direct gain from the same state; scold produces quiet only for the child reached.
- Chorus: up to 3 speak, beliefs independent; the first speaker is the same with or without chorus (as in legacy).
- Individual differences: b0 and r differ across children and across seeds; legacy children all still start at 0.9.
- Stages in bayesian mode: output child still writes reversed, input-test child still uses the other operation or a digit swap, input-teaching child still says no number; every number said is in the allowed set.
- Wrong answers always come from the bug function.
- Session end rules hold (2 right in a row for every erring child, or 40 turns).
- Correct child always right in both modes.
- Env switch: unset = legacy; bad value fails at startup; a session keeps its model after the env changes.
- Calibration: simulate many sessions, bucket the derived P(correct), and check the empirical correct rate per bucket is within a stated tolerance.

## EVAL SCRIPT

New file, e.g. evals/runners/sim_model_compare.py. Do not modify sim_fidelity.py, results.md or recorded results.

Reproduce the BAYESIAN-CHECK.md section 2.10 protocol for BOTH models: same class, each round = pose_problem to child X then one chosen move to X, around the four erring children, until finish or 40 turns, 200 seeds per move. Print per move: mean turns to finish, share ending by 2-in-a-row vs the 40-turn cap, mean belief gain (bayesian), and the spread of starting beliefs. Include the baseline table for legacy so it can be compared with the check's numbers (13.6 / 14.6 / 22.2 / 39.8 / 40.0). Write output to a new file under evals/ (not results.md).

Run the existing fidelity eval (`python -m evals.runners.sim_fidelity --no-write --yes`) in both modes and report the result. If it fails in bayesian mode, report why; do not edit the eval to make it pass. Do not run the live (API) mode.

## DOCS

Write docs/BAYESIAN-MODEL.md as the written specification: latent variable, priors, update equations, derived strength, parameters with defaults, the exact move-effect to T mapping table, what is and is not Bayesian (verdict statistics remain bootstrap over classes and exact McNemar), known limits:

- parameters are chosen defaults, not fitted to real children
- move numbers not reviewed by Seema
- move reader (call 2) unrated, Eval 4 pending
- realism Eval 3 pending
- mixed_level not implemented
- not one hidden variable per concept (no place value / exchange / borrowing state space, no attention, no forgetting, no information-gain question choice)

Plain wording, no claim of real-child validation. Do not edit CLAUDE.md, README, AI_USAGE or any submission doc; list the lines that would need changing instead.

## RULES

- Planned is never described as built; claim only what tests and eval output show.
- Small commits with honest messages, e.g. "add Bayesian child model behind SIMULATOR_MODEL (default legacy)".
- Do not push, deploy or change deployment config. Default must remain legacy.

## FINISH

Report: files changed; test counts (before, after, both modes); golden result; calibration result; eval-script output for both models; fidelity eval result in both modes; the list of doc lines that would need changing; anything that did not work.
