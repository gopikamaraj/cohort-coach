# Practice Class (v1, built in P04)

> **A hypothesis, not a result.** That rehearsing with simulated children improves what a teacher does in class has not been tested by any source we have; it is the hypothesis the pilot tests, and we report the verdict whatever it is (CLAUDE.md rule 13). Nothing on this page claims it works.

A teacher rehearses a technique with five simulated children who make her own class's mistakes. **Code decides every number; Claude only supplies the children's words.** Text mode is built; voice (P07) and the screens (P06) come next.

## The screen (T5)

Five original SVG children with their names and a highlight on whoever spoke (plain shapes, no gender, religion or caste markers; the one who speaks only when named is marked "shy"). A materials tray with bundles of ten, loose sticks and a place-value chart: a tap is a move. A text box, a turn counter ("Turn 2 of 40"), and "End and see feedback". The feedback card shows two strengths and one thing to try with her own words highlighted, a "Checked ✓" badge, a thumbs up or down per point, a "this is wrong" flag and "Try again with the same children" (same seed, same seats). The transcript is saved on the phone only. "Share this session to improve the simulator" is off by default and, for now, only records her choice. Tests: `apps/pwa/e2e/practice.spec.ts` ("a rehearsal of 7 turns with a material tap…", "retry uses the same children", "feedback thumbs and the flag are kept on the phone; sharing is off by default and remembered"); application logs hold none of what she types: `tests/practice/test_api.py::test_no_log_record_at_any_level_holds_what_she_typed`.

Judge mode adds **Show AI layers**: under each reply, the turn's five layers straight from the API's `layers` trace (the label and its confidence, the engine's decision and strength change, the validators, the checker's verdict, latency, tokens and cost, the output and its badge). Pages for the **AI map** (the registry as 8 calls by 5 layers) and the **Audit trail** (the last 50 AI calls as metadata) are linked from the judge script. Teachers never see the overlay.

Seats follow the class: from Home the app sends the class's counts (never a child's answers) and, in judge mode with no class on the phone, the scenario's default mix. Degraded states are shown, not hidden: a template reply says "the connection is slow, so a simple reply was used"; when the day's budget is spent, "Practice is paused for today" with a recorded sample rehearsal to watch; offline, "Practice needs a connection" with everything else still working.

The screenshots in `docs/evidence/screenshots/` (`en-5` to `en-9`) were taken against the API in **recorded mode**, replaying a rehearsal recorded live, so their latencies are replay times, not real ones; real latencies are in `docs/evidence/` (`practice_latency.json`). Live-mode screenshots follow once staging exists.

## How one turn works

```mermaid
sequenceDiagram
    participant T as Teacher (typed, spoken or a tap)
    participant L as Call 2 labeller
    participant E as Engine (engine/simulator.py)
    participant C as Call 1 child voice
    participant G as Gates (validators, pre-filter, call 7)
    T->>L: her line, wrapped as untrusted data
    L-->>E: move, child addressed, posed problem, confidence
    Note over L,E: low confidence becomes "other" (changes nothing);<br/>instruction-like text is forced to "off_task" by code
    E->>E: update strength and engagement; choose speaker and answer<br/>(wrong with probability = strength, number from the bug function)
    E-->>C: turn plan: speaker, intent, answer, steps as data, allowed numbers
    C-->>G: one or two short sentences
    G-->>T: released only on pass, with a Checked badge
    G-->>E: on failure after one retry, a template line is used
```

Two Claude calls and one checker call per turn (calls 2, 1 and 7), plus call 3 at the end. A material tap (bundles, sticks, chart) is a move without a labeller call. Every turn returns a `layers` trace (input, processing, guardrails, evaluation, output) that judge mode renders in P06.

## One live turn, in the five layers

From a live rehearsal (2026-10-17, scripted synthetic lines, `evals/sets/practice_scripts/sub-sfl-en.txt`; the whole session, every turn's `layers`, the feedback card with its two verbatim quotes, and the cost are in `docs/evidence/practice_session_live.json`: 7 turns, median 5344 ms per turn, cost USD 0.0288 including the feedback). Turn 2, an excerpt of that file:

```json
{
 "input": {
  "teacher_text": "Tell me how you got that."
 },
 "processing": {
  "label": {
   "addressed": "Priya",
   "confidence": 0.85,
   "forced": null,
   "move_id": "ask_explain"
  },
  "engine": {
   "speaker": "Priya",
   "intent": "explain",
   "answer": 37,
   "correct": false,
   "error_code": "SUB-SFL",
   "steps": [
    {
     "numbers": [
      2,
      9
     ],
     "op": "cant"
    },
    {
     "numbers": [
      9,
      2,
      7
     ],
     "op": "minus"
    },
    {
     "numbers": [
      5,
      2,
      3
     ],
     "op": "minus"
    }
   ],
   "strength_before": {
    "Priya": 0.9
   },
   "strength_after": {
    "Priya": 0.7
   }
  }
 },
 "guardrails": {
  "validators": [
   "numbers: ok",
   "number_words: ok",
   "length: ok",
   "readability: ok",
   "prefilter: ok"
  ],
  "checker": {
   "failed_items": [],
   "passed": true
  },
  "retries": 0,
  "fallback_used": null
 },
 "evaluation": {
  "latency_ms": 5375,
  "tokens": {
   "cache_read": 5595,
   "in": 976,
   "out": 128
  },
  "cost_usd": 0.00150935
 },
 "output": {
  "badge": "checked",
  "child_line": "I can't do 2 minus 9, Miss. So I did 9 minus 2, that is 7. Then 5 minus 2 is 3. So 37.",
  "source": "ai"
 }
}
```

## The rules the engine follows

From `CLAUDE.md` section 5; the values are tuning parameters in `content/movelists/` and `content/scenarios/`, owned by Seema.

- Five fictional children. Seat 0 is always correct; seats are filled to match her class's error mix (if 40% of the class shows SUB-SFL, 2 of the 5 children do); one child is shy and speaks only when named.
- Each child with an error has a strength from 0 to 1, starting at 0.9, and an engagement level. A child answers wrong with probability equal to her strength, and the wrong number is always the bug function's answer.
- Moves: show with bundles −0.3, ask to explain −0.2, check by adding back −0.2, just tell the rule −0.05, praise raises engagement, scolding lowers it and the child goes quiet for two turns.
- When asked to explain, the engine produces the faulty working as data ("2 minus 9 can't be done, 9 minus 2 is 7, 5 minus 2 is 3"); the model only rephrases it. When she checks by adding back, the engine makes the check ("37 plus 29 is 66, not 52").
- A session ends when every child with the error has been right twice in a row, or at 40 turns (also the judge-mode cap).
- If she names no child, the child she was talking to continues; if she speaks to the class, the engine picks a speaker by engagement.

## Why an engine, not just a prompt

A language model asked to play a confused child can drift: it gets the sum right by accident or invents an error no child makes. Putting the error in code keeps the children faithful to her class, makes sessions reproducible (a seeded generator per turn: the same seed and script replay exactly) and makes the simulator testable. The simulator fidelity eval checks that every number a child says is the engine's, against an independent oracle: `docs/evidence/eval_summary.md` (Eval 2).

## The three calls

| Call | Does | Guards (code) |
| --- | --- | --- |
| 2 labeller | Labels her line with one move from the lesson's list, who she addressed, and a problem she posed | Move list enforced as a JSON-schema enum; low confidence → `other`; injection markers → `off_task` by code; a posed problem must use numbers she said and be a valid two-digit problem; line cut at 600 characters |
| 1 child voice | Puts the plan into 1–2 short sentences in the child's voice | Numbers ⊆ the plan's allowed set; digits only (no number words); at most 30 words; script matches the language; pre-filter; an `answer` line must contain the planned answer; one retry, then a template line; then call 7 |
| 3 feedback | Two strengths and one thing to try, each quoting her words | Each quote verbatim in the turn it cites and in her words, not a child's; points only from the rubric; a strength's turn must carry one of that point's moves; no scores; numbers only from the transcript and the engine; then call 7. If it fails, a card built by code from the rubric and her own lines |

Scolding is named gently by a note the app writes itself (`content/templates/feedback_notes.yaml`), not by the model. The AI never scores a teacher.

## Privacy

- Nothing about a rehearsal is stored on the server. Session state is in memory with a two-hour limit, and the full transcript goes back to her phone.
- The audit trail keeps metadata only (call, model, tokens, cost, latency, validator codes). Practice Class calls are marked `metadata_only`. Her words never reach the audit rows, the judge endpoints or the logs.
- Children are fictional, named from a reviewed list (`content/personas/children.v1.yaml`): first names only, balanced by gender, temperament only, no caste, religion, region or disability markers.
- A real child's voice is never used.

## Modes

| Mode | What it is | Use |
| --- | --- | --- |
| `recorded` | Replays `ai/fixtures/recorded/` (a real session recorded on 2026-10-17 from synthetic lines) | Tests, CI, demos; no network |
| `live` | The Claude API | Real rehearsals; prints and logs cost |
| `record` | Live, and saves each answer as a fixture | Re-recording after a prompt change |
| `stub` | `services/practice/stub_client.py`: rule-based, not a model | Offline demos and API tests; makes no claim about model quality |

Rehearse in the terminal: `python tasks.py practice --scenario sub-sfl --lang en --stub` (or `--live`, `--recorded --script evals/sets/practice_scripts/sub-sfl-en.txt --seed 5`).

## API

`POST /api/practice/sessions` (scenario, language, optional class counts) → session id, the five children (names and which one is shy; not who has which error), materials, move labels. `POST /api/practice/sessions/{id}/turns` (text or material tap) → child, line, numbers, label, badge, explanation, `layers`, latency. `POST /api/practice/sessions/{id}/end` → the feedback card and the transcript.

## What the live runs found

Recorded here because they changed the build; numbers are in `docs/evidence/eval_summary.md`.

- The checker (call 7) first rejected valid child lines: it read the engine's deliberate wrong answers as maths errors and a bare "37, Miss!" as not fitting a lesson. Prompt v2 to v4 tell it the line is a simulated child, that code has already checked every number, and that it judges tone, safety, stereotypes, language, reading level, injection and role.
- With thinking on, the checker sometimes ran out of tokens and returned nothing, so it failed closed. Short rule-bound calls now run with thinking off where the API allows it, with larger token limits.
- The red team found a Hinglish role-reversal line labelled `other` instead of `off_task`. The child stayed in role and nothing changed, but the labeller prompt (v3) now lists off-task examples in four languages.
- Latency: three serial calls (label, child line, check) put the median text turn above the 3 s target. The plan: in voice mode the checker runs while the speech is synthesised (P07), so its time is hidden; the API server will sit near the Claude endpoint (P15); an A/B with Haiku for call 1 was slower and is not adopted. Text mode stays over target until then, and the Practice Class degrades to templates when a call times out.

## Files

`engine/simulator.py` (pure), `services/practice/` (content, templates, session, stub), `ai/calls/c01…c03*.py`, `services/api/practice.py`, `scripts/practice_cli.py`, `content/{movelists,rubrics,scenarios,personas,templates,schemas}`, `evals/runners/sim_fidelity.py`, `evals/sets/sim_fidelity/`.

## Review, impact tags, cues and language (added 2026-10-19)

- **What to practise.** The screen starts with the goal (the error in plain words) and the rubric's "try next" lines in her language. Both come from content files, not from AI.
- **What can I say?** A button opens a cue card: for every move on the list, example lines in her language (`content/movelists/*.yaml`, `examples`), with the example child's name replaced by one of her five children. Tapping a line puts it in the box to change. A move that makes children go quiet is never cued. Four delivery tips (speak slowly, ask then wait, say the name first, praise the trying) are drafts for Seema.
- **Recorded on the phone.** Each rehearsal is saved in IndexedDB as it goes: turns, the move she used (labelled by call 2), language, seed, and the feedback card. Nothing is sent. She can delete one recording or all of them.
- **Review tab.** Lists rehearsals newest first with date, the error practised, number of turns and her tag. Opening one replays it turn by turn (Previous and Next), shows the moves she used with counts, her feedback card and an impact picker, and "Practise again with the same children". The summary is counts ("Rehearsals: 4. Helped: 2. No difference: 1. Did not help: 1."), never percentages.
- **Impact tag.** "Did this rehearsal help?": It helped, No difference, It did not help. It is her own view, kept on the phone, labelled as hers; it is not a score and nothing else reads it (`CLAUDE.md` rules 3 and 11). It does not say anything about whether children improved: only the next check shows that.
- **Language.** The session is created in the language selected in the app; goal, tips, cues, child names, materials, feedback and explanation lines arrive in it. If she switches language mid-rehearsal, a banner offers "Restart in <language>" (same children). A Playwright test checks that the home, check and practice screens (with the cue card open) show no English words in Hindi or Tamil.
- Tested by `apps/pwa/e2e/review.spec.ts`, `apps/pwa/src/lib/review.test.ts` and `tests/practice/test_api.py`.

## Judge-mode demo modes (addendum v3.1, built 22 Oct)

In judge mode the Practice Class has more than free typing. Real teachers never see these.

| Mode | What it is | Where |
| --- | --- | --- |
| Watch | An AI plays the teacher in an experienced or a struggling style, then the normal feedback card shows. Both runs can sit side by side. Playback has pause, step, 2× and skip to feedback. | `#/watch` (`services/practice/watch.py`) |
| Try with hints | Each turn offers three replies built by code from the move list (a strong move, a common mistake, a neutral line), shuffled, with no label until the move tag shows. | Practice Class (`services/practice/hints.py`) |
| Try to break it | Four prepared bad lines run through the real pre-filter; the reason is shown in her language. | Practice Class and the AI map (`POST /api/judge/try-break`) |

Every teacher line in Watch says "AI playing the teacher (demo only)" (call 10). Every child line has an English subtitle (call 1 prompt v3; the digits in both lines must match). Each turn shows a move tag, a confusion meter per child (a word and a bar from the engine's strength) and, on request, "Show the machinery": what code decided, which AI call ran and which checks passed.

**Recorded runs.** `scripts/record_demo_runs.py` runs the live system once per style and language and stores the transcript in `content/demo_runs/` with date, model and prompt versions, seed and scenario version. Judge mode shows the recorded run by default, labelled "recorded run". A live run (capped per hour, `WATCH_LIVE_PER_HOUR`, default 6; cost meter shown) is abandoned for the recorded one if a call fails or a turn takes over 8 s, and the screen says why.

**Stages.** The subtraction scenarios seat three core children, one input-test child (reads the sign as the other operation or swaps the digits of a number) and one output child (says the right number and writes it reversed); an input-teaching child (no method yet, says she is lost) is available through `stage_mix`. The slate under each reply shows what the speaking child wrote. A stage is never shown as a label to the teacher.

**Honest limits.** The two Watch styles show 9 turns each and the experienced run touched more rubric points than the struggling run in the recorded runs (5 of 5 against 1 of 5 for each language); that is one run per cell (`content/demo_runs/*.json`, the `summary` field), not eval 11. Eval 11 (20 runs per style) runs in P13.
