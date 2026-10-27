# P15: production deploy and freeze (handoff, not run)

Status: ⬜ for the judge-mode demo; the pilot service is already live on Google Cloud.

I did not deploy anything. Needs Gopi (accounts and keys):
1. Deploy the judge-mode API and web app per `docs/deploy.md` ("Judge-mode demo deployment"), set the Telegram webhook, and run `JUDGE_MODE=1 python scripts/seed_demo_track.py --languages en --cohort` once.
2. Set Cloud Run minimum instances to 1 for the judging window (1 to 10 Nov); set budget alerts, keeping at least USD 150 in reserve.
3. Re-run `python scripts/ai_proof.py` and `python tasks.py evidence` within 24 hours of submission.
4. Feature freeze: Wed 28 Oct. Only fixes after that.
