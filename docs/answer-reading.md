# Answer reading (call 8): photo of a sheet to one child's boxes (interim, v1 Check page)

In the Check page a teacher can take a photo of one child's answer sheet. The server reads the ten boxes, the boxes fill in, she checks every box (the ones the reader was unsure of are marked and selected first), corrects mistakes with the keypad, and goes to the next child. This is the first working slice of P08; the full check flow on both channels (photos queued offline, confirm steps, no per-child answers kept on the phone) replaces it in P08.

## How a read works

1. **On the phone:** the photo is shrunk to about 1200 px on the long edge as a JPEG (about 80 KB) and sent with the form id (A or B) and nothing else. It is not saved on the phone.
2. **On the server** (`services/api/sheets.py`, `ai/calls/c08_answer_reading.py`): the photo is held in memory, sent to the vision model, and dropped. The size cap (800 KB) is under the 1 MB at which the framework would write an upload to a temporary file, so the photo never touches the disk. Nothing is logged and the photo is never sent back.
3. **Blind read:** the model is told only that there are ten boxes. It never sees the questions, the numbers in them or the expected answers (a test checks the request). It returns the digits in each box and how sure it is.
4. **Judged by code:** digits are normalised (Devanagari and Tamil digits become 0-9). A box is "ok" only if the model is at least 80% sure (a tuning value) and the read is an answer the item recognises: the correct answer, a known error answer, or a known untracked pattern. Everything else is marked "check". A clearly empty box becomes "blank". A box that could not be read stays empty and marked. The expected answers are used only here, after reading.
5. **A broken answer** (wrong number of boxes, a malformed read) is retried once on a stronger model; if that fails too she is told to type. When there is no connection she is told to type, and nothing is sent.
6. **The reads go back to her phone**, where she edits them. The server stores no reads. The audit row for the call holds metadata only (tokens, cost, latency, validator codes), like every other call.

## What this is not

- It does not accept anything silently as correct: every box is hers to check, and the marked ones are where to look first.
- It is not an accuracy claim. A live smoke test on one synthetic printed sheet (not handwriting) read all ten boxes right; that proves the pipeline works, not how well it reads children's handwriting. The accuracy bars (at least 98% of auto-accepted reads correct, at most 15% sent to the teacher) are measured by eval 9 on real pilot sheets in P08 and are pending.
- A blank box currently comes back marked "check" with 0 confidence (the model reports no confidence for an empty box). That is the safe direction; the prompt can be tuned in P08 with its eval.

## Where each part is tested

| Part | Test |
| --- | --- |
| Normalising, in-set and confidence judging, blank handling | `tests/api/test_sheets.py` |
| The model never sees expected answers or operands | `tests/api/test_sheets.py::test_the_model_is_never_told_the_expected_answers` |
| Retry on the stronger model, failure means type | `tests/api/test_sheets.py` |
| Bad, oversized or unknown-form uploads; no photo in the reply; no photo or digits in logs; metadata-only audit row | `tests/api/test_sheets.py` |
| Filling the boxes, marking, corrections, next child, offline, failure; nothing from the photo kept | `apps/pwa/e2e/photo.spec.ts`, `apps/pwa/src/lib/sheets.test.ts` |
