# Content pipeline: from a draft to a lesson a teacher hears

Built in P09 (26 to 27 Oct). It carries the SUB-SFL track (six lessons and one model-lesson script) from the model to a published manifest, and nothing in it removes a gate. The pilot's three template lessons use the same gates and the same review tables (`docs/build/reports/PILOT-MODE.md`).

```text
templates + track definition + strategy library (+ up to 3 approved method cards)
  -> call 5 drafts one part at a time            ai/calls/c05_track_draft.py, prompt v2
  -> slot filler: class numbers only as slots    services/content/slots.py
  -> gate 1  arithmetic, slots only, no Form A or B item, reading level
  -> gate 1b pre-filter, then gate 2 call 7 (the output checker)
  -> review queue: the coach edits, approves or returns with a reason     /api/review/items
  -> track version: the coach's key, then the officer's key               /api/review/versions
  -> publish: voice once per language, manifest                            services/content/publish.py
```

## What is code and what is the model

| Step | Who | Why |
| --- | --- | --- |
| Which parts exist, which strategies, which languages | Data: `content/tracks/sub-sfl.v1/track.yaml`, `content/strategies/`, `content/templates/` | Seema owns it; code never hard-codes it |
| The words of a lesson | Call 5 (Claude Opus), one part per request | The only free-writing step |
| Every class number | Code, as a slot filled at delivery from the cohort's pooled counts | Rule 1: Claude never states a number about a class |
| Every sum | Code (arithmetic validator). A child's intended mistake carries a `[child: 37]` tag the validator accepts | A wrong sum is blocked before the queue |
| A check item (Form A or B) in an example | Code (check-items validator) | The forms stay a clean measure |
| "Is this fit for a teacher" | Call 7, then a person | Gate 2 and gate 3 |
| Approval, activation | People: coach, then officer | Neither key alone publishes |

## The two keys and versions

A track version moves draft, in review, approved (the coach's key), active (the officer's key), retired. An edit makes a new version while the old one stays in use until the new one is active. Every step writes an audit row with the role and the actor; the audit row of an activation holds both keys. Settings the programme may tune (for example the stage-routine threshold) have fixed ranges and go through the same two keys (`services/content/configurable.py`).

## Rejections feed the checker

A return needs one structured reason. The rejection waits in `content/rejections/pending/`; the coach may promote it to `approved/`, and only then does the next call 7 prompt include it as "rejected before, and why". The audit row records which example set the checker saw.

## Publish

Only a version that both keys switched on is published. Each lesson is voiced once per language (reused by content hash), kept to about 0.6 MB per 5 minutes, and the manifest lists lesson ids, audio keys, sizes, script text, badge state, reviewer and activation roles and times. Class numbers are the pooled counts of the cohort's classes, computed by code, and a sum that is only wrong with the real numbers is caught before voicing.

## What was drafted and what came of it

The first live run drafted SUB-SFL v1 in Hindi and English (14 parts). All 14 passed the code gates; call 7 passed 2 and held 12 (`docs/evidence/p09_live_draft_run.txt`).

**Finding, fixed:** most of those holds said the draft stated a class count. The cause was in our gate, not the drafts: in slot mode the text is shown to call 7 with sample numbers in place of the `{class.*}` slots, and call 7's own rule is that it states no statistic, so it read the samples as claims. The checker is now told in its trusted input (`slots_note`) that the numbers stand in for slots that code fills at delivery. A second run in a clean database (`docs/evidence/p09_live_draft_run_after_slots_note.txt`): 12 of 14 reached the coach, 2 held with reasons. The call 7 prompt file did not change; its eval is still P13's job and should include this case.

Cost: the script's estimate was USD 0.60 for 14 parts and each full run cost about twice that, so read the estimate as a rough guide. The local development database also held drafts of some parts from earlier work, so the first run's "queued" marks show only the parts that were new; the cumulative spend is `python tasks.py budget`.

Held drafts are not lost: they sit in the queue as `held_by_checker`, and a coach can read, edit (the edit is checked again) and approve them.

## Not built (cut up front)

Tamil lessons (the track file declares `ta` but nothing is drafted), the citations pass 2 ("why this move" lines with citations), stage routines, and a live Message Batches run (the request builder is built and tested on recorded data). The model run (T12) was built on 29 Oct; see "The model run" below.

## The model run

`services/content/model_run.py`. About three minutes of the track's move done well, with the same five simulated children, for a teacher to hear before she rehearses.

1. **Render.** From an *approved* model-lesson script only. The teacher's lines are the script's teacher lines (slots filled with the engine's worked example, tags stripped), nothing else. The move for each line is assigned by code from the track's strategy order (pose the problem, the strategies, praise), and the Practice Class engine and call 1 answer as the children, so every number a child says is the engine's. A fixed seed freezes it.
2. **Review.** It becomes a review item of type `model_run`; the coach approves or returns it (gate 3, audited). The same script version is never rendered twice: a new render needs a new approved script version.
3. **Voice.** Only after approval, once: an adult voice (`ritu`) for the teacher and each child's own stock voice, joined as OGG/Opus mono at 16 kbps (12 kbps if it would pass 0.35 MB per three minutes). The file is named by a hash of its words and voices.
4. **Publish.** The track manifest lists it as a `model_run` part with a caption that says simulated.

Routes (coach renders, approves and returns; officer voices): `/api/review/model-runs`. Not built: a screen for it in the review queue (the routes and tests exist), and a live render with call 1 (the tests use the offline stub client).
