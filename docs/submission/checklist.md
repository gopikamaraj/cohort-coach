# Submission checklist (deadline Sun 1 Nov, 11:59 pm; we submit Sat 31 Oct)

Status as of 27 Oct. A box is ticked only with evidence. Human-owned items name their owner.

## Demo link

- [ ] **Judge-mode demo deployed and open logged out on desktop and phone.** Not deployed: only the pilot is live on Google Cloud (`docs/deploy.md`). Recipe: "Judge-mode demo deployment" in `docs/deploy.md`. Owner: Gopi.
- [ ] Run `JUDGE_MODE=1 python scripts/seed_demo_track.py --languages en --cohort` once on that deployment. Owner: Gopi.
- [ ] `/start judge` works on the bot (needs the Telegram token and the webhook). Owner: Gopi.
- [ ] Cloud Run minimum instances set to 1 on every service before 1 Nov. Owner: Gopi.
- [ ] Uptime monitor on. Owner: Gopi.

## Source code

- [x] README opens with the idea, the judge steps, the status table and "Where AI is used" (generated).
- [x] `AI_USAGE.md` current; `python scripts/gen_ai_usage.py --check` and `tests/test_ai_usage_doc.py` pass. Re-run `python scripts/ai_proof.py` within 24 hours of submission. Owner: Gopi.
- [ ] Repo public. Owner: Gopi.
- [ ] Secret scan clean on the final commit (no key, no `.env`, `gcp/` stays untracked and `*-key.json` ignored). Owner: Gopi.
- [x] No real child or teacher data in the repo (the synthetic data is labelled simulated).

## Video and deck

- [ ] Video recorded on the phone, 2:55, public on YouTube, plays logged out (`docs/submission/video-script.md`, `shot-list.md`). Owner: Shivani.
- [ ] Hindi and Tamil audio and `video-captions.srt`. Owner: Shivani.
- [ ] Deck built from `docs/submission/deck.md`, uploaded. Owner: Shivani.
- [ ] Every link in the deck and README works. Owner: Shivani.

## Claims

- [x] Every number in the README, docs and deck source is from a generated file (`docs/evidence/numbers.md`, `evals/results.md`, `docs/evidence/cost_per_teacher.md`, `docs/evidence/data_budget.json`).
- [x] Problem claims cite `docs/design/evidence-digest.md` with source and page, keep scope notes, and cite no opinion source as evidence that something works.
- [x] No capability is claimed above its status: cut items (calls 4, 6, 9, the model run, Tamil lessons, the Telegram thread, the visit brief) are listed as not built.
- [x] Simulated practice is called a hypothesis everywhere.

## Evidence still missing (be honest on the slides)

- Real low-end phone run and Slow 3G measurement (`docs/evidence/device_test.md`). Owner: Gopi.
- Human-rated evals: realism, labeller agreement, feedback usefulness, answer-reading accuracy, track drafts accepted (shown as pending in `evals/results.md`). Owners: Seema, Shivani.
- Text-turn latency is over target: median 4968 ms against 3000 ms (`evals/results/practice_latency.json`); voice 7515 ms against 5000 ms.
- Round 3 and round 4 user testing (`docs/feedback-log.md` is empty). Owners: Seema, Shivani.
- The Hindi and Tamil wording of every string is a first draft. Owner: Shivani.
