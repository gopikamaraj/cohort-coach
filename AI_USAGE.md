# How Cohort Coach uses AI

Status words used below, and nothing else: **Specified** (in docs only), **Built** (code exists), **Verified** (`docs/evidence/ai_usage_proof.json` shows PASS for it). A claim is never ahead of the repo: `tests/test_ai_usage_doc.py` checks the file paths and the Verified rows.

## 1. The principle

AI does language: vision, simulation, labelling, feedback, drafting, checking. Code does maths and decisions: every number, every right or wrong, every stage diagnosis, every score. A child's line is released only after validators and a checker pass.

## 2. Where AI is central (the five product moments)

| Moment | What AI does | What code does | Call ids | Entry file |
| --- | --- | --- | --- | --- |
| Answer-sheet reading | Reads the digits a child wrote from a photo, blind (never told the answers) | Normalises digits, accepts only plausible confident reads, sends the rest to the teacher, diagnoses, counts, stages | 8 | `ai/calls/c08_answer_reading.py` |
| Practice Class turn (simulated children) | Labels what the teacher did; puts the engine's chosen answer into a Grade 3 child's words, with an English subtitle | Holds every child's state, decides who speaks and whether the answer is right, chooses the wrong number from the bug function, validates every number, releases only after the checker passes | 1, 2, 7 | `services/practice/session.py` |
| Teacher feedback card | Writes two strengths and one thing to try, each quoting her words | Checks every quote is verbatim, keeps points to the rubric, rejects any score | 3, 7 | `ai/calls/c03_feedback.py` |
| Track and method-card drafting (Specified) | Turns a mentor's sentences into a method card and drafts lessons from approved content, with citations | Checks arithmetic, fills class numbers as slots, validates every citation id and phrase, then humans approve | 4, 5, 7 | `ai/prompts/c04_method_capture.v1.md`, `ai/prompts/c05_track_draft.v1.md` (prompts only; the call modules arrive in P09 and P11) |
| Judge-mode demo teacher | Plays the teacher in an experienced or a struggling style | Allows only approved moves and scenario numbers, falls back to a template line, refuses outside judge mode | 10 | `ai/calls/c10_demo_teacher.py` |

## 3. Capability map

| Capability | Why it is used here | Call(s) | File(s) | Status | Proof |
| --- | --- | --- | --- | --- | --- |
| Vision | Child handwriting on a phone photo is the input of the whole loop | 8 | `ai/calls/c08_answer_reading.py`, `services/api/sheets.py` | Verified | `docs/evidence/ai_usage_proof.json#image_input` |
| LLM-simulated children from code-held state | Teachers rehearse with children who make her class's mistakes; the engine decides, the model only speaks | 1, 2 | `engine/simulator.py`, `ai/calls/c01_child_voice.py`, `services/practice/session.py` | Built | `tests/practice/test_session.py`, `tests/engine/test_simulator_stages.py` |
| Classification into a fixed taxonomy | A teacher's free line becomes one move from a fixed list, or `other` | 2 | `ai/calls/c02_move_label.py`, `ai/schemas.py` | Built | `tests/practice/test_calls_1_2.py` |
| Structured outputs (JSON schema) | Every call returns a model the code re-validates | 1, 2, 3, 7, 8, 10 | `ai/client.py`, `ai/schemas.py` | Verified | `docs/evidence/ai_usage_proof.json#structured_output` |
| Citations API | Each method-card step and each "why this move" line points at the sentence or page it came from (the API refuses citations together with structured output, so these calls use two passes) | 4, 5 | `docs/design/cohort-coach-design.md` (AI layer), `docs/build/BUILD_PROMPTS.md` (P09, P11), `docs/build/DECISIONS.md` | Specified | `docs/evidence/ai_usage_proof.json#citations` (an API-level check of the request shape; the product code is not built) |
| LLM as checker with check-then-release | A second model checks tone, safety, language and fit before any child line is shown | 7 | `ai/calls/c07_checker.py`, `ai/guard/gates.py` | Built | `docs/evidence/ai_usage_proof.json#structured_output` shows the verdict parses; the red-team result arrives in P13 |
| Reflective feedback | Gives private, quote-backed feedback after a rehearsal, with no score | 3 | `ai/calls/c03_feedback.py`, `ai/validators/quotes.py` | Built | `tests/practice/test_call_3.py` |
| Offline drafting via Message Batches | Drafting six lessons in two or three languages is cheap and not urgent | 5 | `docs/build/BUILD_PROMPTS.md` (P09 step 3) | Specified | `docs/evidence/ai_usage_proof.json#batches` (an API-level check; the batch drafting script is not built) |
| Prompt caching | The long stable system prompt of every live call is read from cache | all | `ai/client.py` | Verified | `docs/evidence/ai_usage_proof.json#caching` |
| Model tiering | Sonnet writes and reads, Haiku labels, checks and reads sheets, Opus drafts offline | all | `ai/config.py`, `ai/registry.py` | Built | `tests/ai/test_registry.py` |
| Effort and thinking settings on live turns | Lowest effort that passes the call's eval; thinking off where the model allows it | 1, 2, 7, 10 | `ai/config.py` | Built | `tests/ai/test_registry.py` |
| Untrusted-text tagging | Teacher, mentor and reflection text is wrapped as data and never obeyed | all | `ai/client.py` | Built | `tests/ai/test_client.py` |
| Speech in and out (not Claude) | Teachers speak; Sarvam turns speech to text and back, Claude works on text | none | `services/speech/stt.py`, `services/speech/tts.py` | Built | `docs/speech.md` |
| Claude Code with subagents, used to build | Three read-only reviewers audit every phase for integrity, privacy and judge fit | none | `.claude/agents/integrity-auditor.md`, `.claude/agents/privacy-guardian.md`, `.claude/agents/judge-reviewer.md` | Built | `docs/build/reports/P08-addendum-v3.1.md` |
| Offline picture-item authoring (call 11) | Drafts the JSON spec of one new counted object for a topic pack; code draws it, counts it and checks it | 11 | `ai/calls/c11_sprite_author.py`, `services/api/sprite_gates.py`, `ai/prompts/c11_sprite_author.v1.md` | Built | `tests/sprites/test_authoring.py` (every gate has a failing case; no live run yet) |
| Meshy MCP (authoring time only) | Would make classroom materials for future topic packs, reviewed before use | none | `docs/build/PARKING.md` | Specified | none: parked, not built, never runs in the product |

## 4. Call registry

Generated from `ai/registry.py` by `scripts/gen_ai_usage.py`. Do not edit between the markers. Call 9 (reflection pointer) is Specified and joins the registry in P10.

<!-- REGISTRY:START -->
| Id | Purpose | Model | Input | Output schema | Gates | Fallback |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Say one short line as a simulated Grade 3 child in the Practice Class. | `claude-sonnet-5-5` | Child persona, language, the teacher's labelled move, and the exact wrong answer the engine chose. | `ChildLine` | code validators; pre-filter; call 7 (check-then-release) | a template line from the engine's own numbers |
| 2 | Label what the teacher just did with one move from a fixed list. | `claude-haiku-5-5` | One line the teacher said or typed, wrapped as untrusted data, and the technique's fixed move list. | `MoveLabel` | JSON schema; confidence floor | label `other` (changes nothing) |
| 3 | After a rehearsal, give two strengths and one thing to try, each quoting her words. | `claude-sonnet-5-5` | The rehearsal transcript (stays on her phone unless she shares it) and the rubric of moves. | `Feedback` | code validators; pre-filter; call 7 | a template card; nothing is shown that failed a check |
| 4 | Turn a mentor's spoken answers into a method card, citing her sentences. | `claude-sonnet-5-5` | The mentor's transcribed answers, split into numbered sentences. | `MethodCard` | code validators; pre-filter; call 7; mentor approval; reviewer approval | no card: the mentor is asked to try again or a coach is asked to help |
| 5 | Draft a 3-week track: six 5-minute lessons and one model-lesson script. | `claude-opus-5-5` | The error, language, up to 3 approved method cards and the lesson plan structure. | `TrackDraft` | code validators; pre-filter; call 7; reviewer approval; mentor approval | no draft: the lesson waits for a human; a line without a valid citation is dropped |
| 6 | Group a week of teacher reflections into themes; code counts them. | `claude-haiku-5-5` | Short reflections with names and schools removed by code first. | `Digest` | names stripped by code; pre-filter; call 7 | no digest this week |
| 7 | Check anything headed to a teacher against the rubric and return a structured verdict. | `claude-haiku-5-5` | Candidate text, audience, language, target error, and what code already checked. | `Verdict` | gate 2 | fail goes to a human; nothing is released |
| 8 | Read the digits a child wrote on an answer-sheet photo, blind. | `claude-haiku-5-5` | One sheet photo (base64 JPEG). It carries no name or roll number. The model is never told the expected answers. | `SheetRead` | read outside expected answers goes to the teacher | the teacher types the answers |
| 10 | Play the teacher in a Practice Class Watch run, in an experienced or a struggling style, so a visitor can compare. | `claude-haiku-5-5` | The scenario, the approved move list, the style, the transcript so far and the engine's state of the five simulated children. | `DemoTeacherTurn` | code validators; pre-filter; judge session only | the move's own template line |
| 11 | Draft the JSON spec of one new sprite item (a counted object) for a topic pack, at authoring time only. | `claude-sonnet-5-5` | A short brief for one object (for example 'a mango') and the ids of the items that exist. | `SpriteItemDraft` | code validators; pre-filter; call 7 (words); coach approval; officer enablement | no draft: nothing is shown; the author is told which rule failed |
<!-- REGISTRY:END -->

## 5. What AI does not do

- It never decides whether a child is correct.
- It never computes a number that is displayed (call 8 transcribes digits and call 1 repeats the engine's number; both are re-checked by code).
- It never authors cohort posts.
- It never pairs children.
- It never generates art at run time: every picture is drawn by code from data. Call 11 drafts picture items offline only, and nothing it drafts reaches a teacher before the code gates, call 7, a coach and a programme officer.
- It never sees child names: names are stripped before any call, and answer sheets carry none.

## 6. Guardrail layers

Gate 1 code validators (`ai/validators/`), gate 1b rule-based pre-filter (`ai/validators/prefilter.py`), gate 2 the output checker, call 7 (`ai/calls/c07_checker.py`), gate 3 human approval for track content and method cards (Specified, P09 and P11), gate 4 the teacher's "this is wrong" flag (`ai/guard/flags.py`). Badges: "Checked" after gates 1 and 2, "Checked and Reviewed" after gate 3 (`ai/guard/badges.py`). Every call has a deterministic fallback (section 4) and writes one audit row with metadata only (`ai/audit.py`). Full description: `docs/guardrails.md`.

## 7. Verify it yourself in 5 minutes

1. `python tasks.py test` runs the Python and web tests with no paid calls.
2. `python scripts/ai_proof.py` runs one cheap live check per capability (about USD 0.10) and rewrites `docs/evidence/ai_usage_proof.json`.
3. Open `docs/evidence/ai_usage_proof.json`: each check says PASS, FAIL or SKIPPED, with model ids and token counts.
4. Open one audit row: `GET /api/judge/audit` in judge mode shows the last calls (call, model, prompt version, tokens, cost, validators, verdict) and never any text.
5. `python tasks.py eval all` runs the evals; the results file is generated by it in P13, and until then the eval runners are in `evals/runners/` and human-rated evals read "pending".
6. `python scripts/gen_ai_usage.py --check` fails if section 4 has drifted from `ai/registry.py`.

## 8. Cost and limits

Prices and their source are in `ai/pricing.yaml`. Spend by call, model and day: `python tasks.py budget` (`scripts/budget.py`). A measured live Practice Class session is in `docs/evidence/practice_session_live.json`. The cost-per-teacher script and its assumptions file are planned for P13 and not built. Live traffic is stopped by `AI_BUDGET_USD_TOTAL`, `AI_BUDGET_USD_DAILY` and a hard ceiling (`ai/client.py`); judge mode shows recorded runs by default and switches to them when a call fails, a turn is slow or the hourly live cap is reached (`services/practice/watch.py`).
