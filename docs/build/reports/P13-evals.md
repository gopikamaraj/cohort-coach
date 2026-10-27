# P13: evals, red team, cost, latency (reduced)

Status: 🟡. Everything here is generated or measured; see `evals/results.md` (written by `scripts/eval_results.py`, never by hand).

## Done
- Red-team set grown from 22 to 52 cases (`evals/sets/redteam.yaml`); live run PASS, 0 of 52 unsafe reach a teacher (`evals/results/redteam_live.json`).
- Fix loop: the first live run showed call 7 confusing sample numbers with unfilled slots, holding good drafts. Root cause was the gate's sample-number fill; fixed (`slots_filled_by_code` and `SLOTS_NOTE` in `ai/calls/c07_checker.py`), after which 12 of 14 drafts reached the coach (`docs/build/reports/P09-content-pipeline.md`).
- Cost per teacher per track from measured per-call costs and stated assumptions (`scripts/cost_per_teacher.py`, `docs/evidence/cost_per_teacher.md`).
- Results page generator with tests (`tests/test_eval_results.py`): human-rated evals show "pending".

## Not met, reported as such
- Practice Class text turn latency median 4968 ms against 3000 ms: FAIL. Voice is also over its target.
- Pending, no number shown: realism, labeller agreement, feedback usefulness, answer-reading accuracy, track drafts accepted, call 10 and call 11 live runs.

## For humans
- Shivani: replace the placeholder red-team prompts (the 30 added cases are placeholders for her real ones), label the 150 lines, key the answer sheets.
- Gopi: decide whether to tune latency (shorter prompts, lower effort) or accept the FAIL in the deck.
