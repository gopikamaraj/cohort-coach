---
bodhan_tts: pending
bodhan_stt: pending
date:
decided_by:
---

# Speech gates: may Bodhan AI be the first provider?

The front matter above is the record the app reads at startup (`services/speech/chain.py`): while a gate is `pending` or `fail` and Bodhan is first for that function, the API logs a warning (it never blocks).

A gate is set to `pass` or `fail` only by a person, with `--record NAME`, after the evaluation:

- **Text to speech** (`bodhan_tts`): `python scripts/speech_eval_aggregate.py <ratings folder> --record "Name"` after raters score the blinded listening pack (`python tasks.py speech-eval-pack`). Default thresholds (content/speech_gates.yaml, to be confirmed by Gopi and Seema): Bodhan's mean naturalness within 0.3 of Sarvam's, and under 5% of its clips rated "numbers wrong".
- **Speech to text** (`bodhan_stt`): `python tasks.py speech-eval-stt --record "Name"` on team members' recordings (protocol: `docs/evidence/speech-eval/PROTOCOL.md`). Default thresholds: a character error rate no more than 5 points worse than Sarvam's, and key maths terms heard correctly at least 90% of the time.

Each script prints every gate against its threshold whether or not it records. Results recorded below.
