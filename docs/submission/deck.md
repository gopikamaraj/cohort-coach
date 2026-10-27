# Deck source: Cohort Coach

Slide by slide, in order. Every number comes from a generated file named on the slide's source line; every claim about teachers or the school system cites `docs/design/evidence-digest.md` (source and PDF page) and keeps its scope note. Shivani builds the slides from this file; nothing here is a finished design. Build status is the README's table: say only what is built.

## 1. Title

Cohort Coach. Grouping primary teachers for training by the mistake their pupils make. Team A-Z 0-9 · Hack2skill × Anthropic "AI for Foundational Learning" · Challenge 3 (Teacher Support and Training).

## 2. The problem (five figures)

Training is generic, rarely practised, and not followed up; monitoring counts inputs.

| Figure | Source (digest row, page) | Scope note to say aloud |
| --- | --- | --- |
| 3 of 4 States skip a needs analysis before training | FLN 54 | A five-State study |
| 75% say training rarely demonstrates or practises | FLN 56; NITI 147 | One State |
| 80% of monitoring indicators track inputs | FLN 72, 73 | A five-State study |
| Under a third of teachers trained yearly | FLN 54 | A five-State study |
| 1,04,125 single-teacher schools | NITI 130 | National |

BaSE figures cover EdTech-using teachers only. IDR and APU are opinion and are not used as evidence that anything works.

## 3. The idea and the loop

A termly 10-item check shows which mistake each class makes. Teachers whose classes share a mistake form a cohort across schools and get a 3-week track on that one mistake. A mentor is a teacher whose class fixed it. The next check says whether children improved, against a comparison group. Loop diagram: check, cohort, track, practice, next check, mentor, next cohort.

## 4. The assumption we have not proved

Rehearsing a move with simulated children before using it on real ones is a hypothesis. No source we have tests it. The pilot tests it, and we will report the verdict whatever it is. Children are shown to improve only by the next check, never by lessons delivered or sessions held.

## 5. AI in layers (the call table)

The README's "Where AI is used" table, generated from `ai/registry.py`; each call's input, processing, guardrails, evaluation and output. Show the Practice Class turn as a diagram: teacher's words, move label (call 2), engine chooses the wrong answer, child's line (call 1), checker (call 7), voice. Say which calls are built (1, 2, 3, 5, 7, 8, 10, 11) and which were cut (4, 6, 9): `AI_USAGE.md` is the source.

## 6. Guardrails

Code computes every number; the model only speaks around it. Four gates: code validators, rule-based pre-filter, the output checker (call 7), a person (the coach, then the officer's key). Every AI card has "this is wrong". Rejections feed the checker. Evidence: red team 52 cases, 0 unsafe reach a teacher (`evals/results.md`); the held-draft finding and its fix (`docs/content-pipeline.md`).

## 7. Real scenarios

Low connectivity, low data, low-cost phones. A text fallback for every voice step; the check and the lessons queue offline; only the Practice Class needs a live connection, and the deck says so. Computed worst-case data per track: `docs/evidence/data_budget.json` (met with text practice, missed if every session uses voice). Web app first load: `docs/evidence/bundle_size.json`. Not yet measured: Slow 3G and a real low-end phone (`docs/build/PROGRESS.md`).

## 8. User inputs and testing (two slides)

Slide A: how input was collected (the round 3 and 4 plan, `docs/user-testing/`). Slide B: "You said, we changed" from `docs/feedback-log.md` with commit links, with confidence notes. If a round has not happened, the slide says so; it shows no invented quotes.

## 9. The pilot, built and live

Pilot mode (`PILOT_MODE=1`) on Google Cloud: a coordinator uploads pre-test sheets (private bucket, consent reference, retention), the system reads them, drafts three lessons from the class counts, a coach approves, and the audio is shared on WhatsApp. `docs/build/reports/PILOT-MODE.md`, `docs/deploy.md`.

## 10. Honest statistics

Officer view: track results with an interval, groups under 5 hidden, a failed track counts against the track, not the teacher. Evidence: `evals/results.md` row 8 (statistics), `docs/evidence/demo_verdicts.md`. Cost per teacher per track: `docs/evidence/cost_per_teacher.md` (a range; assumptions stated).

## 11. Roadmap (two slides)

Slide A: a one-block pilot with a DIET from January 2027, then a district; WhatsApp; IVR; literacy tracks. Slide B: "Beyond Grade 3 maths", the topic-pack anatomy (`docs/roadmap.md`). Integration with state assessment data, UDISE+ identifiers, existing training records.

## 12. What we cut, and what we need

The cuts, each logged (`docs/build/PARKING.md`). Needed from partners: a block, a DIET, schools that agree to the pre-test, a coach and an officer.
