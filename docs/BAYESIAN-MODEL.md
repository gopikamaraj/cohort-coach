# The 32-state Bayesian child model (Practice Class, behind `SIMULATOR_MODEL`)

Status: see the build report. Parameters are build defaults, not reviewed by an educator, not fitted to real children.

Build report: `docs/build/reports/BAYES-32-STATE.md`. Build prompt: `docs/build/BAYESIAN-32-STATE-BUILD-PROMPT-v2.md` (it supersedes the one-variable prompt; see section 10). This document is the written specification. The independent oracle (`evals/runners/bayes_oracle.py`) is written from it, not from the code.

## 1. The switch and the split

- `.env` `SIMULATOR_MODEL` = `legacy` | `bayesian`. Unset or empty means `legacy`. Any other value stops the API at startup: "SIMULATOR_MODEL must be legacy or bayesian (or unset for legacy)".
- `.env` `BAYES_PARAMS` (optional) is the parameter file; default `content/bayes/params.v1.yaml`. It is read and validated at startup only when `SIMULATOR_MODEL=bayesian`.
- `engine/sim_switch.py` is the one factory. `new_session` returns the legacy `SessionState` or the bayesian `BayesState`, and `plan_turn` dispatches on the state's type, so a session keeps its model when the environment changes later.
- `engine/simulator.py` is not edited: its SHA-256 is recorded in `tests/fixtures/legacy_sim.sha256` and checked by a test. Legacy output is checked turn for turn against `tests/fixtures/legacy_sim_golden.json` (every scenario, seeds 1 to 20, two scripts), directly and through the factory.
- The legacy path never imports `engine/bayes` (checked in a subprocess). The factory imports it lazily.
- The only edits to shared code: `services/practice/session.py` calls the factory, and `services/api/main.py` calls `check_startup` instead of the old one-variable check.

## 2. The contract with the rest of the engine (Step 0)

The bayesian planner returns `engine.simulator.TurnPlan` and children as `engine.simulator.Child`, with the same field names and types. These are the fields the rest of the code reads:

| Reader | Fields |
| --- | --- |
| `services/practice/session.py` (`take_turn`, `_engine_layer`, `children_view`) | plan: `turn`, `speaker`, `intent`, `answer`, `correct`, `error_code`, `problem`, `steps`, `mood`, `strength_before`, `strength_after`, `allowed_numbers`, `written`, `chorus` (each a `TurnPlan`). Child: `name`, `error`, `shy`, `strength` (the confusion meter), `engagement`, `quiet_turns`. State: `turn`, `children`, `finished`, `finished_reason` |
| `services/api/practice.py` | state: `turn`, `finished`, `children` (`name`, `shy`) |
| `services/practice/watch.py`, `services/content/model_run.py` | state: `problem`, `next_problem`, `children`, `finished` |
| `services/practice/faces.py` via `children_view` | `engagement`, `strength`, `quiet_turns`, `shy`, and the plan's `intent` and `correct` |
| `services/practice/templates.py` | plan: `speaker`, `intent`, `steps`, `answer` |
| `ai/calls/c01_child_voice.py` (call 1) | plan: `intent`, `mood`, `answer`, `steps`, `allowed_numbers`, `move_id`, `speaker`, `spoken_correct` |
| `ai/calls/c03_feedback.py` (call 3) | nothing from the plan: the turn records (teacher text, move id, child text) |

Types: `turn` int; `move_id`, `behaviour`, `intent`, `mood`, `stage` str; `speaker` str or None; `problem` `Problem` or None; `answer`, `written` int or None; `correct`, `spoken_correct` bool or None; `error_code` `ErrorCode` or None; `steps` tuple of `Step`; `allowed_numbers` frozenset of int; `strength_before`, `strength_after` maps of name to float; `chorus` tuple of `TurnPlan`; `trace` an empty tuple under this model (the bayesian extras go to a separate debug trace).

**Problem choice (legacy).** A move whose behaviour is `answer` takes the posed problem if it is valid, else the next scenario problem `problems[next_problem % 6]`. A move that needs a problem (`explain`, `work_aloud`, `doubt`) when none is on the board takes the next scenario problem. The candidate set is the scenario's own `problems` list (six items per scenario).

**Addressing (legacy, confirmed).** A move named to one child reaches her directly and every other child as something overheard, at the scenario's `overhear` share (0.5) of its effect on strength and engagement, never the going-quiet. A move to the class or to no one (`addressed` None or not one of the five names) applies the full effect to every child. `other` and `off_task` are neutral: only the turn counter changes.

**Move ids** (all move lists): pose_problem, ask_explain, show_bundles, exchange_ten, regroup_ten, decomposition, compensation, show_chart, check_back, order_probe, tell_rule, repeat_rule_louder, give_the_answer, praise, scold; plus the neutral other and off_task. **Error codes:** SUB-SFL, SUB-NODEC, ADD-NOCARRY, PV-HEARD, PV-REVERSE.

**Teacher notes.** No teacher note reaches the Practice Class: `start_session` and the API's session request carry the error, language, class counts, seed and judge flag only. So `note_tags` is an optional parameter of the factory (and of `start_session`), tested, and not wired to any screen.

## 3. Content files (`content/bayes/`)

All are build defaults, not reviewed by an educator.

### 3.1 Families (`families.v1.yaml`)

| Family | Codes | place_value | exchange | written_step | Sibling pair | Habit shift |
| --- | --- | --- | --- | --- | --- | --- |
| subtraction | SUB-SFL, SUB-NODEC | tens and ones | one ten = ten ones | the written borrow-and-decrement step | SUB-SFL ↔ SUB-NODEC | SUB-SFL → SUB-NODEC under rule-drill moves |
| addition | ADD-NOCARRY | tens and ones | one ten = ten ones | the written carry step | none (sibling prior 0) | none |
| place_value | PV-HEARD, PV-REVERSE | tens and ones | one ten = ten ones | writing a two-digit numeral in place order | PV-HEARD ↔ PV-REVERSE | none |

Roles: **target** is the scenario's error code; **sibling** is its pair (none for addition). In the SUB-NODEC scenario the target is SUB-NODEC and the sibling SUB-SFL, so the shift SUB-SFL → SUB-NODEC there moves a child from sibling to target.

### 3.2 Moves (`moves.v1.yaml`)

| Move | cov_P | cov_E | cov_W | scaf | conf | demo | rule_drill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pose_problem | 0 | 0 | 0.1 | 0.3 | 0 | no | no |
| ask_explain | 0.2 | 0.3 | 0.2 | 0.9 | 0.3 | no | no |
| show_bundles | 0.6 | 0.9 | 0.3 | 0.5 | 0.2 | yes | no |
| exchange_ten | 0.3 | 0.9 | 0.5 | 0.5 | 0.2 | yes | no |
| regroup_ten | 0.3 | 0.9 | 0.5 | 0.5 | 0.2 | yes | no |
| decomposition | 0.8 | 0.5 | 0.3 | 0.6 | 0.2 | yes | no |
| compensation | 0.5 | 0.3 | 0.2 | 0.5 | 0.1 | yes | no |
| show_chart | 0.9 | 0.3 | 0.4 | 0.4 | 0.2 | yes | no |
| check_back | 0.1 | 0.2 | 0.4 | 0.8 | 0.8 | no | no |
| order_probe | 0.3 | 0.2 | 0.2 | 0.8 | 0.9 | no | no |
| tell_rule | 0 | 0 | 0.6 | 0 | 0.1 | no | yes |
| repeat_rule_louder | 0 | 0 | 0.3 | 0 | 0 | no | yes |
| give_the_answer | 0 | 0 | 0 | 0 | 0 | no | no |
| praise | 0 | 0 | 0 | 0 | 0 | no | no |
| scold | 0 | 0 | 0 | 0 | 0 | no | no |

The engagement change eng(m) is read from the legacy move list (praise +0.15, scold −0.30, show_bundles +0.10, …), not repeated. `other` and `off_task` are neutral (all zero, eng 0, reach 0). Scold sets quiet for `quiet_turns` (2) for the children it reaches directly, as legacy. The loader refuses a move list whose move ids are not all in this table.

### 3.3 Teacher-note tags (`note_tags.v1.yaml`)

| Tag | Likelihood ratios |
| --- | --- |
| pv_secure | place_value=1 ×3.0 |
| pv_shaky | place_value=1 ×0.33 |
| bundles_used_before | exchange=1 ×2.0 |
| rule_drilled | habit=sibling ×2.0 (subtraction only); written_step=1 ×1.5 |
| new_topic | exchange=1 ×0.5; written_step=1 ×0.5 |

Unknown tags are refused. No free text, no AI parsing.

### 3.4 Parameters (`params.v1.yaml`)

Each is stored as {default, low, high, provenance: "build default, not reviewed by an educator"}. low and high are the default ±30%, clipped to the valid range; whole numbers of turns are rounded. The loader checks every parameter is present, in its valid range, and low ≤ default ≤ high.

| Group | Parameter | Default | Low | High | Meaning |
| --- | --- | --- | --- | --- | --- |
| Prior | p_P0 | 0.6 | 0.42 | 0.78 | P(place_value=1) at start |
| Prior | p_E0_P1 | 0.4 | 0.28 | 0.52 | P(exchange=1) at start if place_value=1 |
| Prior | p_E0_P0 | 0.1 | 0.07 | 0.13 | P(exchange=1) at start if place_value=0 |
| Observer | r_diag | 0.85 | 0.595 | 1.0 | trust in the diagnosed habit |
| Observer | obs_W0 | 0.9 | 0.63 | 1.0 | observer's starting P(written_step=0) |
| Response | g0 | 0.05 | 0.035 | 0.065 | right by chance: habit, not P∧E |
| Response | g_PE | 0.25 | 0.175 | 0.325 | right by reasoning: habit, P∧E |
| Response | slip | 0.05 | 0.035 | 0.065 | wrong despite the written step |
| Response | c_none | 0.2 | 0.14 | 0.26 | right: no habit, no written step, not P∧E |
| Response | c_none_PE | 0.6 | 0.42 | 0.78 | right: no habit, no written step, P∧E |
| Response | g_nm | 0.05 | 0.035 | 0.065 | right: no method, item needs the step |
| Response | c_nm_easy | 0.6 | 0.42 | 0.78 | right: no method, item needs no step |
| Priming | delta0 | 0.3 | 0.21 | 0.39 | priming strength on the demo turn |
| Priming | rho | 0.5 | 0.35 | 0.65 | decay per turn |
| Priming | prime_window | 2 turns | 1 | 3 | turns the priming lasts |
| Learning | beta0 | −4.0 | −5.2 | −2.8 | intercept |
| Learning | beta_cov | 3.0 | 2.1 | 3.9 | coverage weight |
| Learning | beta_fit | 1.5 | 1.05 | 1.95 | fit weight |
| Learning | beta_scaf | 1.0 | 0.7 | 1.3 | scaffolding weight |
| Learning | beta_att | 2.0 | 1.4 | 2.6 | attention weight |
| Learning | beta_over | 1.0 | 0.7 | 1.3 | overload weight |
| Learning | fit_E_noP | 0.3 | 0.21 | 0.39 | fit for exchange when place_value=0 |
| Learning | fit_W_noE | 0.3 | 0.21 | 0.39 | fit for written_step when exchange=0 |
| Habit | gamma0 | −3.0 | −3.9 | −2.1 | intercept for breaking the habit |
| Habit | gamma_conf | 2.5 | 1.75 | 3.25 | conflict weight |
| Habit | gamma_E | 1.0 | 0.7 | 1.3 | exchange-idea weight |
| Habit | gamma_att | 1.5 | 1.05 | 1.95 | attention weight |
| Habit | shift_rate | 0.15 | 0.105 | 0.195 | habit shift probability under a rule drill |
| Forgetting | h0_P | 0.005 | 0.0035 | 0.0065 | per-turn hazard, place_value |
| Forgetting | h0_E | 0.01 | 0.007 | 0.013 | per-turn hazard, exchange |
| Forgetting | h0_W | 0.03 | 0.021 | 0.039 | per-turn hazard, written_step |
| Forgetting | c0 | 2 | 1.4 | 2.6 | practice scale |
| Attention | tau | 3 turns | 2.1 | 3.9 | time constant |
| Attention | K_push | 2.0 | 1.4 | 2.6 | scale on the legacy engagement change |
| Attention | addressed_bonus | 0.1 | 0.07 | 0.13 | pull up when reached directly |
| Attention | neglect | 0.15 | 0.105 | 0.195 | pull down when not reached directly |
| Attention | neglect_after | 3 turns | 2 | 4 | when the neglect pull starts |
| Attention | overload_drag | 0.1 | 0.07 | 0.13 | pull down per overload unit |
| Overload | ov_window | 3 turns | 2 | 4 | look-back window |
| Overload | ov_free | 2 | 1 | 3 | heavy moves allowed before overload |
| Overload | heavy_cov | 0.5 | 0.35 | 0.65 | coverage that makes a move heavy |

The attention base and starting value are the scenario's `start_engagement` (0.6); the overhear share is the scenario's `overhear` (0.5). Neither is repeated.

**Spec note.** The response defaults give a mean starting wrong rate of 0.902 for a target-habit child on an item that needs the step, matching legacy's start_strength 0.9: P(P∧E) at start = 0.6 × 0.4 = 0.24, so 0.95 × (1 − 0.24) + 0.75 × 0.24 = 0.722 + 0.18 = 0.902.

## 4. State

Each erring child holds a true hidden state as a map `{"place_value": 0|1, "exchange": 0|1, "written_step": 0|1, "habit": none|target|sibling|no_method}`; below, P, E, W and H. `no_method` means no stable method. Traces show the actual error code next to the role.

A belief is a joint array with one named axis per variable, shape (2, 2, 2, 4). Axis order (place_value, exchange, written_step, habit) and habit order (none, target, sibling, no_method) are declared once, in `engine/bayes/state.py`; every conversion goes through it. The flat index is ((P·2 + E)·2 + W)·4 + H (row-major), used for the 32 × 32 transition matrix and for serialisation.

The correct child (seat 0) is outside the model: always right, as legacy.

## 5. The simulated child (generative model)

### 5.1 Class and prior

The class (names, error code per seat, stages, shy child) comes from the legacy `fill_seats`, read-only, so a seed gives the same class under both models. Each erring child's start state is drawn from `Random(f"bayes:prior:{seed}:{seat}")`:

- written_step = 0;
- habit = the seat's role (target or sibling by its error code), or no_method if the seat's stage is input-teaching;
- (place_value, exchange) jointly from **one uniform** over the four cells in row-major order (0,0), (0,1), (1,0), (1,1), with weights (1−p_P0)(1−p_E0_P0), (1−p_P0)·p_E0_P0, p_P0(1−p_E0_P1), p_P0·p_E0_P1;
- teacher-note tags reweight those four cells (only factors on place_value or exchange) and are renormalised before the draw. In the generative prior, tags never change habit or written_step.

### 5.2 Response table O(kind | s, item)

Kinds: correct, bug_target, bug_sibling, no_answer.

- `bites(code, item)`: the bug function for that code gives a wrong number different from the correct answer.
- `needs_step(item)`: at least one bug in the child's family bites on the item.

**Item needs no step:** every state answers correct with probability 1, except habit no_method, which answers correct with c_nm_easy and no_answer with 1 − c_nm_easy.

**Item needs the step:**

| W | H | correct | bug_target | bug_sibling | no_answer |
| --- | --- | --- | --- | --- | --- |
| 1 | none | 1 − slip | slip | 0 | 0 |
| 1 | target | 1 − slip | slip | 0 | 0 |
| 1 | sibling | 1 − slip | 0 | slip | 0 |
| 1 | no_method | 1 − slip | 0 | 0 | slip |
| 0 | target | g(P,E) | 1 − g(P,E) | 0 | 0 |
| 0 | sibling | g(P,E) | 0 | 1 − g(P,E) | 0 |
| 0 | none | c(P,E) | 0 | 0 | 1 − c(P,E) |
| 0 | no_method | g_nm | 0 | 0 | 1 − g_nm |

with g(P,E) = g_PE if P=1 and E=1, else g0; c(P,E) = c_none_PE if P=1 and E=1, else c_none.

- **Collapse:** if a bug kind's own bug does not bite on the item, its probability moves to correct (the sibling bug never bites when the family has no sibling).
- **Priming** of strength δ (5.6), after the collapse: correct′ = correct + δ·(1 − correct); every other kind is multiplied by (1 − δ).
- The wrong number for a bug kind is drawn uniformly from the sorted wrong answers of that code for the problem (`engine.simulator.wrong_answers` over `engine/bugs.py`, the correct answer excluded).

### 5.3 Stage channels

| Stage | Behaviour |
| --- | --- |
| core | the drawn kind is said and written as it is |
| input-teaching | handled by habit = no_method; no channel |
| output | any kind other than correct becomes the legacy output form: says the right number, writes it reversed. Where reversing gives the same number or the answer ends in 0, there is no output form and the child answers right (as legacy) |
| input-test | any kind other than correct becomes the legacy input-test form: the other operation's result or a digit swap (a dictation misread by one digit). Where there is no such option, the child answers right (as legacy) |

The forms are copies of the legacy helpers (`_rev`, `_near`, the options of `_misheard`). The 32 states set the probability of an error at every stage; the stage sets its form. The error code on a bug answer is the code of the habit that produced it; on a stage form it is the seat's code, as legacy.

### 5.4 Answers

Each fresh answer draws exactly two uniforms from `Random(f"bayes:answer:{seed}:{turn}:{seat}")`: the first picks the kind by cumulative probability in the order correct, bug_target, bug_sibling, no_answer; the second picks the number (index ⌊u·n⌋ into the sorted wrong answers or the input-test options). A child answers at most once per turn. `work_aloud` always draws a fresh answer; `explain` and `doubt` repeat the child's last answer if she has one (legacy draws twice under `work_aloud`; the second draw replaces the first, so one draw is the same rule).

### 5.5 Learning transitions

Each turn, for each erring child, from the start-of-turn state. **Reach** r, matching legacy addressing: 1 for a direct move (the named child, or every child when the move is to the class or to no one); `overhear` (0.5) for every other child; 0 for the neutral moves `other` and `off_task`. A child is **reached directly** when r = 1 from a direct move.

**Concept learning.** For X ∈ {P, E, W} with X = 0: if cov_X(m)·r > 0,

p_learn(X) = σ(beta0 + beta_cov·cov_X(m)·r + beta_fit·fit_X(s) + beta_scaf·scaf(m)·r + beta_att·(a − 0.5) − beta_over·ov)

else 0. σ(x) = 1/(1 + e^(−x)). fit_P = 1; fit_E = 1 if P=1 else fit_E_noP; fit_W = 1 if E=1 else fit_W_noE. Here a is the child's attention after this turn's filter step (5.7, which comes before the transitions in the turn order) and ov her overload this turn (5.8).

**Habit**, for H ∈ {target, sibling}, one categorical draw:

- p_break = σ(gamma0 + gamma_conf·conf(m)·r + gamma_E·E + gamma_att·(a − 0.5)) if conf(m)·r > 0, else 0. Breaking sets H = none.
- p_shift = shift_rate·r if rule_drill(m), E = 0, W = 0 and the family defines a shift from the child's current code; shifting moves H to the other code's role.
- If p_break + p_shift > 1, both are scaled to sum to 1. H stays with the remaining probability.
- H = no_method becomes none when W flips 0 → 1 in the same turn. H = none never changes.

**Forgetting**, every turn whether the child is reached or not: each X = 1 reverts to 0 with hazard h_X = h0_X·exp(−c/c0), where c is her count of correct answers this session on items that need the step.

**Matrix.** The 32 × 32 matrix T[s, s′] is the product of the place_value factor, the exchange factor and the joint (written_step, habit) factor, enumerated from these rules for every start state. Every row sums to 1.

**Draws.** `Random(f"bayes:trans:{seed}:{turn}:{seat}")`, exactly four uniforms per erring child per turn, in the order P, E, W, H, drawn whether used or not. For X = 0, X′ = 1 when u_X < p_learn(X); for X = 1, X′ = 0 when u_X < h_X. Habit: H′ = none when u_H < p_break; else the shifted role when u_H < p_break + p_shift; else H.

### 5.6 Priming

A demo move that reaches a child with r > 0 primes her at strength δ0·r, age 0, on the demo turn itself. On later turns δ = δ0·r·rho^age, while age < prime_window; then it ends. A new demo resets it. Priming changes answers only (5.2), never the state.

### 5.7 Attention (low-pass filter)

a_(t+1) = a_t + α·(target_t − a_t), α = 1 − exp(−1/tau), a_0 = start_engagement.

target_t = clamp(base + K_push·eng(m)·r + addressed_bonus·[reached directly] − neglect·[not reached directly for ≥ neglect_after turns] − overload_drag·ov, 0, 1), base = start_engagement.

The count of turns not reached directly resets to 0 on a turn she is reached directly and goes up by 1 otherwise (neutral moves count as not reached). Attention applies to all five children. It replaces engagement in the bayesian path: it sets the speaker weights (a + 0.05), the mood (legacy thresholds: flat below 0.35, bright above 0.75, else calm; small after a scold; doubtful on a wrong answer under a check-back) and the engagement field the faces read.

### 5.8 Overload

ov = max(0, n_heavy − ov_free), where n_heavy counts the moves with max(cov_P, cov_E, cov_W) ≥ heavy_cov that reached the child directly in the last ov_window turns, including this one.

### 5.9 Turn order

1. Move label in: id, addressee, optional posed problem.
2. Reach for every child; the counters; overload; attention; priming.
3. Transitions: the true state (transition generator) and the observer's predict step (6.1).
4. Quiet from a scold (the children reached directly).
5. Problem: the posed problem if valid; where legacy would take the next scenario problem, the highest information gain (6.3).
6. Speaker: the named child; otherwise weights a + 0.05 over the children who are not shy and were not quiet at the start of the turn, from `Random(f"bayes:speak:{seed}:{turn}")`.
7. Chorus, up to chorus_max, from `Random(f"bayes:chorus:{seed}:{turn}")` (how many, then who, weights a + 0.05). The first speaker is the same with or without a chorus.
8. Answers for the speaker and the chorus (5.2 to 5.4); the observer's update (6.1) after each.
9. Bookkeeping: streaks (the legacy rule), the count c, the quiet countdown, the strengths, the trace, the finish check (every erring child right twice in a row, or 40 turns).

**Differences from legacy order, reported:** legacy chooses the problem (5) before it applies the move (2 to 4). Here the move is applied first, because the information-gain choice uses the predicted belief. The problem does not enter the transitions, so nothing else changes. Answers (8) are drawn in the order speaker then chorus, as legacy, though step 7's chorus choice is listed before them.

### 5.10 What the planner hands on

The legacy contract (section 2), with:

- strength = 1 − P(correct | true state, current problem, priming), after the stage channel; before any problem, on the first scenario item that needs the step. The correct child's strength is 0;
- engagement = a; mood by the legacy rule on a;
- `strength_before` and `strength_after` for the erring children a teaching move (any coverage or conflict) reached;
- every number in a line from the allowed set built the legacy way (the problem's numbers when there is an answer or working, the answer, the written answer, the numbers of the working).

The bayesian extras go only to a debug trace (`plan_turn_traced`, logged at debug level by `take_turn`), never to the API response: the true state map with its error code, belief marginals as a map, entropy, the most likely state, p_learn values, p_break, p_shift, attention, reach, overload, priming, the observer's predictive P(correct) before each answer, and the information-gain ranking.

**Serialisation.** `engine.bayes.planner.to_dict` gives plain data: the true state as a map, each belief as a list of 32 floats with the axis declaration of `engine/bayes/state.py`, the counters and the parameter values. The session store is not changed.

## 6. Belief engine, soft evidence, question choice

### 6.1 Observer

Per erring child, a belief b over the 32 states. It never reads the true state and consumes no randomness.

Start: the plain generative prior over (place_value, exchange); habit r_diag on the seat's diagnosed code's role, with 1 − r_diag shared equally over the other habit values the family allows (none, the other code of the pair if there is one, no_method); written_step 0 with obs_W0 and 1 with 1 − obs_W0; then the teacher-note tags (6.2) on every variable they name.

Each turn:

- **Predict** (every erring child, every turn): b ← b·T_t, with T_t built from the same rules and the same observable context (move, reach, attention, overload, c).
- **Update** (only when the child gives a fresh answer): b ← normalise(b ⊙ L), L(s) = P(observed outcome | s, item, priming, stage). For a core (or input-teaching) child the outcome is the number said, or no number: P(n | s) = O(correct|s)·[n = correct] + O(bug_target|s)/|W_t|·[n ∈ W_t] + O(bug_sibling|s)/|W_s|·[n ∈ W_s], where W_t and W_s are the two codes' wrong-answer sets. For an output or input-test child the outcome is error form versus correct: P(form | s) = 1 − O(correct|s), or 0 when the item has no form.

Outputs: marginals P(place_value=1), P(exchange=1), P(written_step=1) and P(habit=·); entropy in bits, H(b) = −Σ b(s) log2 b(s); the most likely state; the predictive P(correct) = Σ b(s)·P(correct | s) for any item.

### 6.2 Soft evidence

For each tag, multiply the weight of every state by the tag's likelihood ratio for the variables it names, then renormalise. The generative prior applies tags to (place_value, exchange) only; the observer's start belief to every variable the tag names. No tags gives exactly the plain prior. The class diagnosis enters the observer through r_diag. Not wired to the UI (section 2).

### 6.3 Next question by expected information gain

When the planner must choose the problem itself, it scores each scenario item:

EIG(item) = H(b) − Σ_y P(y | b, item)·H(b | y, item), with P(y | b) = Σ b(s)·L_y(s) and b | y ∝ b ⊙ L_y,

over the observable outcomes y of 6.1, with the predicted belief and the child's priming this turn. The score is for the named child, or summed over the erring children when the move is to the class or to no one (a named correct child scores 0 everywhere). The highest score wins; ties go to the earliest item in scenario order. The problem just used is not repeated unless it is the only one. No new problems are made. The ranking goes to the trace.

## 7. Tests

Under `tests/engine/bayes/` (existing tests are not weakened or deleted).

### 7.1 Split and contract

The simulator hash; legacy identical to the golden fixtures, directly and through the factory, with the default and with `SIMULATOR_MODEL=legacy`; the 183 simulator and practice tests named in `docs/build/reports/BAYESIAN-CHECK.md` 2.11 pass in both; both models return the same plan fields and types; every number said is in the allowed set; wrong numbers come only from bug functions; the correct child is always right; the switch tests of section 1; a bayesian session state round-trips through JSON.

### 7.2 Structure

State map ↔ array coordinates round-trips for all 32 states, with the order only from `state.py`; every transition row and every response row sums to 1 (±1e-9) for every move, reach, context and item in the scenarios; the collapse rule; the stage forms match the legacy forms; on an item that needs no step every state except no_method answers correct (1.0); exactly four transition draws per erring child per turn, and the belief engine and EIG consume no randomness; the mean starting wrong rate is 0.902.

### 7.3 Golden cases G1 to G7, worked

**G1 Response row.** Item 52 − 29, target SUB-SFL. SUB-SFL takes the smaller digit from the larger in each column: ones |2 − 9| = 7, tens 5 − 2 = 3, so 37; SUB-NODEC borrows without reducing the tens: ones 12 − 9 = 3, tens 5 − 2 = 3, so 33; correct 23. Both bite, so the item needs the step. State (P0, E0, W0, target): W = 0, H = target, not P∧E, so g = g0 = 0.05: **correct 0.05, bug_target 0.95** (number 37). With P = 1 and E = 1: g = g_PE = 0.25: **0.25 / 0.75**.

**G2 No step needed.** Item 58 − 23: ones 8 − 3 = 5, tens 5 − 2 = 3, no borrowing. SUB-SFL gives 35, SUB-NODEC gives 35, both equal the correct 35, so neither bites and the item needs no step: **correct 1.0** for (P0, E0, W0, target).

**G3 Learning.** show_bundles, direct (r = 1), child (P1, E0, W0, target), a = 0.6 in the formula, ov = 0. fit_E = 1 because P = 1. x = −4.0 + 3.0·0.9 + 1.5·1 + 1.0·0.5 + 2.0·(0.6 − 0.5) − 1.0·0 = −4.0 + 2.7 + 1.5 + 0.5 + 0.2 = 0.9. **p_learn(E) = σ(0.9) = 0.7109.**

**G4 Attention.** a = 0.6, tau = 3, α = 1 − e^(−1/3) = 0.283469. Turn 1, a scold reaching her directly: eng = −0.30, target = 0.6 + 2.0·(−0.30)·1 + 0.1 = 0.1; a1 = 0.6 + 0.283469·(0.1 − 0.6) = **0.4583**. Turn 2, `other` addressed to no one: neutral, r = 0, not reached directly but only for 1 turn (< 3, no neglect), target = 0.6; a2 = 0.4583 + 0.283469·(0.6 − 0.458266) = **0.4984**.

**G5 Forgetting.** h_W = 0.03·exp(−c/2): **c = 0: 0.03; c = 2: 0.03·e^(−1) = 0.0110.**

**G6 Bayes update.** Slice P0, E0, W0 with habit prior target 0.85, sibling 0.05, none 0.05, no_method 0.05; observe 23 (correct) on 52 − 29. Likelihood of 23: target g0 = 0.05; sibling g0 = 0.05; none c_none = 0.2; no_method g_nm = 0.05. Products 0.0425, 0.0025, 0.0100, 0.0025; sum 0.0575. **Posterior target 0.7391, sibling 0.0435, none 0.1739, no_method 0.0435.**

**G7 Information gain.** Child with habit = target, P0, E0, P(W=1) = 0.5. H(b) = 1 bit. On 52 − 29: W = 1 gives 23 with 0.95 and 37 with 0.05; W = 0 gives 23 with 0.05 and 37 with 0.95. P(23) = P(37) = 0.5; each posterior is (0.95, 0.05), entropy 0.2864 bits. **EIG(52 − 29) = 1 − 0.2864 = 0.7136 bits.** On 58 − 23 every state answers 35 with probability 1: **EIG = 0 bits.** The planner **chooses 52 − 29**.

### 7.4 Behaviour tests B1 to B8

Each uses at least 200 seeds; the thresholds are fixed here. A failure is reported with its measured value; the threshold, the parameters and the model are not changed to pass. Protocol "2.10" is that of `docs/build/reports/BAYESIAN-CHECK.md` section 2.10: SUB-SFL, no class counts, and each round is `pose_problem` to child X then the move to child X, round the erring children, until the session ends or 40 turns.

| Test | What it checks | Threshold |
| --- | --- | --- |
| B1 Determinism | the same seed gives identical sessions (true states, beliefs, answers) on the 12-move script; seeds 5 and 6 differ | identical for every seed; 5 ≠ 6 |
| B2 Teaching quality | under protocol 2.10, mean turns to finish | show_bundles, exchange_ten and decomposition each below both tell_rule and repeat_rule_louder |
| B3 Prerequisites | one direct show_bundles at equal attention (0.6) to every erring child with E = 0, from the prior; share who learn exchange, by place_value | rate(P=1) − rate(P=0) ≥ 0.10 |
| B4 Attention | protocol 2.10 with show_bundles, with a scold before each teaching move versus a praise | the scold schedule finishes later on average and has lower mean attention |
| B5 Overload | four show_bundles to one child on consecutive turns versus the same four spaced by pose_problem turns; mean p_learn(exchange) for a child with P = 1, E = 0 over the four teaching turns | consecutive lower than spaced |
| B6 Priming | after a demo, P(correct) on the next item that needs the step, for children without the written step, with and without priming | higher on the demo turn and the next; equal after prime_window turns; the written step never depends on priming |
| B7 Forgetting | at least 20,000 child-turns with the written step known and no correct practice (c = 0), a neutral move; then the same with practice (c = 4) | reversion rate within ±0.01 of h0_W; with practice lower |
| B8 Belief recovery | protocol 2.10, each seed one session, the moves taken in turn; at session end, and the observer's predictive P(correct) before each fresh answer | most likely written_step = true one for ≥ 85% of erring children; calibration within ±0.08 in every bucket (ten equal-width buckets) with ≥ 50 observations |

## 8. Evals (`evals/out/bayes/`)

| Script | What it does |
| --- | --- |
| `evals/runners/bayes_oracle.py` | Reimplements sections 4 to 6 from this document without importing `engine/bayes` or `engine/simulator` (it reads `engine/bugs.py`). Checks G1 to G7 and 1,000 random (state, item, move, context) cases against `engine/bayes`: response rows, transition rows, attention, forgetting, Bayes updates, EIG. Pass: maximum absolute difference ≤ 1e-9 |
| `evals/runners/bayes_fidelity.py` | The sim_fidelity protocol (4 errors × 5 seeds × 10 scripted turns = 200 turns) on the bayesian planner. Each planned answer is correct, a wrong answer the oracle gives for the child's current code, or the legacy stage form; every number in the line is in the allowed set. Bar: 100% |
| `evals/runners/bayes_model_compare.py` | Protocol 2.10 for both models, 200 seeds per move: mean turns to finish, the share ending by two-in-a-row versus the 40-turn cap; for bayesian, mean concepts learned, final entropy and recovery rate; the legacy baseline 13.6 / 14.6 / 22.2 / 39.8 / 40.0; whether the legacy ties separate and which coverage values cause it. (A new file: `evals/runners/sim_model_compare.py` from the one-variable build is left as it is.) |
| `evals/runners/bayes_sensitivity.py` | Every parameter at low and at high one at a time, plus 50 seeded Latin-hypercube draws across all bands: per move the median and 5–95% band of mean turns to finish, how often the top tier keeps its members, and the parameters that change the move ranking |
| `evals/runners/bayes_replay.py` | Replays every recorded Watch run in `content/demo_runs/` on its class and seed through both models: turns, finish reason, wrong-answer rate by turn, final belief marginals (bayesian). Recorded runs are not edited |

## 9. Not modelled, not validated

- Parameters are build defaults, not reviewed by an educator and not fitted to real children.
- Nothing carries across sessions: a session lives 2 hours in a server dictionary.
- The move reader (call 2) is unrated (Eval 4 pending), and every transition depends on its label.
- Realism against real classes (Eval 3) is pending.
- The `mixed_level` flag is not implemented. Different starting states come from the prior, not from the flag.
- Verdict statistics remain a bootstrap over classes and an exact McNemar test, not Bayesian.
- The belief engine appears in the debug trace only. It chooses the next problem by information gain inside the bayesian planner, but no screen shows a belief.

## 10. The one-variable model this replaces

The earlier build (`docs/build/BAYESIAN-MODEL-BUILD-PROMPT.md`, `engine/child_model.py`) added a one-variable model: Bayesian knowledge tracing with a Beta prior and a responsiveness per child, selected by `SIMULATOR_MODEL=bayesian` inside `engine/simulator.py`. This build supersedes it. Because `engine/simulator.py` must not be edited, that code stays in place: the factory always passes the legacy model explicitly, so no session can select the one-variable model, and its unit tests still run against the module directly. `SIMULATOR_MODEL=bayesian` now means the 32-state model. Code that calls `engine.simulator.new_session` without a model (some scripts and the legacy evals) still reads `engine.child_model.model_from_env`, so with `SIMULATOR_MODEL=bayesian` set in the shell those scripts would get the one-variable model: run them with the variable unset.
