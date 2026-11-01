# Speech-to-text test: how to record

This tests how well Bodhan and Sarvam turn a teacher's spoken maths talk into text. It feeds the speech-to-text gate in `docs/evidence/speech_gates.md`.

**Who records:** team members only (Gopi, Seema, Shivani, or other adults who agree). **Never a child, and never a classroom.** Don't say real children's or schools' names.

**What to record:** 30 short utterances per language (English, Hindi, Tamil), each 3 to 15 seconds, spoken the way a teacher talks in class. Mix:
- numbers said as words ("fifty-two", "बावन", "ஐம்பத்து இரண்டு") and three-digit numbers ("three hundred and forty-six");
- sums ("seventy-four minus forty-six", "703 में से 468");
- the key maths terms: borrow, regroup, ten, bundle, tens, ones, carry (English words inside Hindi and Tamil sentences too, as teachers say them);
- a few lines in the Practice Class style ("Priya, show it with the bundles").

**How:**
- Use real phones: at least two different phones, one of them a low-end Android.
- Record in the phone's own recorder app or WhatsApp voice note. The script converts WebM, M4A, OGG, MP3 and WAV.
- Record some in a quiet room and some with ordinary background noise (a fan, a corridor).

**Where the files go:** `data/speech-eval/` (git-ignored: nothing here is ever committed). Put the audio files in `data/speech-eval/<language>/`, and write `data/speech-eval/references.csv` with one row per file:

```csv
id,language,file,reference,phone,noise
en-01,en,en/en-01.m4a,"Seventy-four minus forty-six: we have to borrow a ten.",redmi-9,quiet
hi-01,hi,hi/hi-01.ogg,"चौहत्तर में से छियालीस: हमें एक दहाई borrow करनी होगी।",galaxy-a10,fan
```

`reference` is exactly what was said, written the way you would write it; numbers can be digits or words, since both are normalised before comparing. `phone` and `noise` are free tags, used to break the results down.

**Run:** `python tasks.py speech-eval-stt` checks the files and prints the estimated cost. Add `--yes` to transcribe with both providers, and `--record "Your name"` to record the gate. Raw transcripts stay in `data/speech-eval/results.json` on your machine. Only the numbers go to `evals/results/speech_eval_stt.json`.

**Privacy:** these are adults' voices recorded for this test, with their agreement. Delete `data/speech-eval/` when the evaluation is done. Bodhan's and Sarvam's own handling of the audio is in `docs/vendors/bodhan/TERMS-CHECK.md` (to fill in) and Sarvam's terms.
