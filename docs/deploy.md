# Deploying staging (and later production)

Status: **pilot mode is deployed on Google Cloud (26 Oct); the generic recipe below is still not run on Render, Neon or Cloudflare.** See "Google Cloud pilot deployment" at the end for what is live. The rest of this page is the original recipe.

Status of the original recipe: **written, not yet run.** It needs hosting accounts and secrets (Gopi). Nothing below has been executed on a real host; steps marked "verify" are the checks to run once it is live. The defaults follow OD-3 in `docs/build/DECISIONS.md`: an always-on small API instance, managed Postgres, S3-compatible storage for published audio, and static hosting for the PWA. No plan that sleeps during 1–10 Nov.

## What runs where

| Part | Where (default) | Notes |
| --- | --- | --- |
| API (FastAPI) | Render web service, or Railway or Fly.io, from the `Dockerfile` at the repo root | Paid always-on instance (no sleeping) |
| Database | Neon or Supabase Postgres | `DATABASE_URL=postgresql+psycopg://…` |
| Audio storage (P09 onwards) | Cloudflare R2 | `S3_*` variables; nothing is stored yet |
| PWA | Cloudflare Pages, Vercel or Netlify, static | Build `apps/pwa`, output `dist` |

## Secrets and settings

Set these on the API host (never in git, never in the PWA build). `.env.example` lists every key.

| Variable | Value |
| --- | --- |
| `ANTHROPIC_API_KEY` | your key |
| `AI_MODE` | `live` |
| `JUDGE_MODE` | `1` on the public demo only (every role, the demo teacher, sample sheets, the judge routes). Leave it unset anywhere real teachers are stored: it fails closed |
| `AI_BUDGET_USD_TOTAL`, `AI_BUDGET_USD_DAILY`, `AI_BUDGET_USD_HARD` | caps for non-judge traffic and the hard ceiling (defaults 350, 40, 500) |
| `DATABASE_URL` | the managed Postgres URL |
| `PWA_ORIGIN` | the PWA's https origin, for example `https://cohort-coach.pages.dev` (no trailing path). The API answers browsers from this origin only |
| `PUBLIC_BASE_URL` | the API's https URL |
| `SARVAM_API_KEY`, `TELEGRAM_*`, `S3_*` | needed from P07, P10 and P09 |

On the PWA host, set one build variable: `VITE_API_BASE` = the API's https URL (no trailing slash). It is public by nature; it holds no secret.

## Steps

1. **Database.** Create a Postgres database; copy the connection string and change the scheme to `postgresql+psycopg://`. Tables are created on first start (Alembic comes with the stable schema; see DECISIONS).
2. **API.** Create a web service from this repo using the `Dockerfile` (it installs `.[prod]` and runs uvicorn on `$PORT`). Choose an always-on plan, set the variables above, deploy. Health check path: `/api/health`.
3. **PWA.** Create a static site from this repo: root directory `apps/pwa`, build command `npm ci && npm run build`, output directory `dist`, build variable `VITE_API_BASE`. Make sure the host serves `index.html` for the app and `sw.js`, `manifest.webmanifest` and `workbox-*.js` as files.
4. **Link them.** Put the PWA's URL in the API's `PWA_ORIGIN` and redeploy the API. Put the API's URL in the PWA's `VITE_API_BASE` and rebuild the PWA.
5. **Record the URLs** in `docs/build/PROGRESS.md` under Environments.

## Verify (run these once it is live)

- `curl https://<api>/api/health` returns `{"status":"ok", …}`.
- `curl -i -X OPTIONS https://<api>/api/practice/sessions -H "Origin: https://<pwa>" -H "Access-Control-Request-Method: POST"` shows `access-control-allow-origin: https://<pwa>`; the same with another origin shows none.
- Open the PWA URL on a phone: it opens straight into judge mode; Load a simulated class; My class shows counts; Practice runs a turn and the child answers (this is the human check for the P06 acceptance on a real phone over mobile data).
- `https://<pwa>/#/audit` lists the AI calls just made, with no text anyone typed.
- Server logs contain request lines only: search them for a phrase you typed in Practice (there must be no match).
- Spend: `python tasks.py budget` against the production database (set `DATABASE_URL`) shows cost per call.

## Cold starts and keep-alive

A plan that sleeps makes the first judge wait. Use an always-on instance. As a belt and braces, from 1 to 10 Nov an uptime monitor can request `/api/health` every 5 minutes (free tiers of most monitors allow this). The health route never calls an AI model, so keep-alive costs nothing.

## Rollback

Redeploy the previous image or commit on the API host; on the PWA host, promote the previous deployment. Data in the database is class-level counts and audit metadata only, so a rollback loses nothing a teacher typed.

## Google Cloud pilot deployment (live since 26 Oct)

Project `fln-cohort-coach`, region `asia-south1`. Pilot mode only (`PILOT_MODE=1`): sign-in, Upload sheets and Intervention audio. Not the judge-mode demo.

| Part | Where |
| --- | --- |
| API | Cloud Run service `cohort-coach-api`, built from the root `Dockerfile` with `gcloud run deploy --source .`. URL https://cohort-coach-api-1097171252131.asia-south1.run.app. Min instances **0** (cold start on the first request after idle), max 3, 1 GiB, **CPU always allocated** (`--no-cpu-throttling`): sheet reading runs as a background task after the upload reply, and with throttled CPU it never ran |
| Web app | Cloud Run service `cohort-coach-pwa`: nginx serving `apps/pwa/dist`, built with `VITE_PILOT_MODE=1` and `VITE_API_BASE` set to the API URL. URL https://cohort-coach-pwa-1097171252131.asia-south1.run.app |
| Database | Cloud SQL Postgres 16, instance `cohort-coach-db` (`db-f1-micro`), database `cohort`, reached over the Cloud SQL socket |
| Buckets | `fcc-build-app-sheets-bucket` (private; CORS allows PUT from the web app only; lifecycle deletes after 97 days) and `fcc-build-app-audio-bucket` (private). Public access prevention enforced, uniform access on |
| Identity | The API runs as `gcs-storage-admin@fln-cohort-coach.iam.gserviceaccount.com` (no key file): Storage Object Admin on both buckets, Secret Manager Secret Accessor, Cloud SQL Client, and Token Creator on itself so Google's IAM service signs the URLs |
| Secrets | Secret Manager: `anthropic-api-key`, `sarvam-api-key`, `pilot-accounts`, `pilot-token-secret`, `db-password`. Rotate by adding a new version, then redeploy or update the service |

Redeploy the API: `gcloud run deploy cohort-coach-api --source . --region asia-south1 --project fln-cohort-coach` (keep the existing settings; add flags only to change them). Redeploy the web app: rebuild `apps/pwa` with the two build variables above, then deploy it the same way from a folder holding the `dist` output, an nginx config and a small Dockerfile.

**Before 1 Nov:** set the API's minimum instances to 1 (`gcloud run services update cohort-coach-api --min-instances=1 --region asia-south1`) so no judge waits on a cold start.

**Checked in headless Chromium at phone width on 26 Oct:** sign-in (a wrong key shows the message), deep links redirect to sign-in or Upload sheets, upload through a signed URL straight to the bucket, the stored sheet then read by call 8 (the test image was not a real sheet, so it was flagged "needs a look", which is correct), the Intervention audio page and its "No sheets read yet" state, the Hindi and Tamil switch, and sign-out. The test sheets were then deleted with the delete-for-school action. A sheet left at "stored" (for example if the instance restarts mid-read) is now read again the next time the counts are viewed, once it is two minutes old (`sheets.retry_stuck`, tests in `tests/pilot/test_retry.py`).

**Checked with the 28 synthetic sheets (`data/synthetic_sheets`, class S1-3A pre-test, all made up) on 26 Oct:** uploaded through the app, 24 read and 4 flagged "needs a second look" by the live reader; Generate audio made three English lessons from 23 read sheets (the live checker held one back, two went to the coach); approving lesson 2 voiced it with Sarvam and published a 27.8 s AAC file; the signed download link served it. Three faults found and fixed on the way, each with a test: the image lacked `docs/design/pilot_forms.golden.json` (500 on Generate; a 500 reaches the browser without CORS headers, so the app showed "No signal"), the image lacked `ffmpeg` (voicing failed with `audio:unavailable`), and Postgres refused a lesson pointing at a review item not yet written (SQLite ignores foreign keys, so the pilot tests now turn them on). A lesson row left at "draft" by a dead request no longer blocks Generate. The test sheets and lessons are still in the live database and buckets; they are labelled SIMSCH / SIM-SYNTHETIC-NO-REAL-CONSENT."+nl+nl+"**Checked from outside with curl on 26 Oct:** health, 404 on every non-pilot route, CORS limited to the web app, sign-in (401 on a wrong key), and an authenticated read of the database. **Not yet checked:** the web app in a browser or on a phone, a real sheet upload through a signed URL, a live Claude sheet read, and Sarvam voice (the key was rejected earlier).

**Checked live on 26 Oct, words-first flow:** the coach approved lesson 3's text and the audio bucket still held only lesson 2's earlier file (approval made no audio). A fresh browser with no sign-in opened the lesson link (no staff pages, no key field), showed the approved text with the Checked and Reviewed badge, and made no audio by itself. The first tap on Download audio made the file in 7.0 s and saved `cc-pilot-slot3-en.m4a`; a second visitor's tap took 0.5 s and the bucket gained no new file. New setting: `PILOT_VOICE_DAILY_MAX` (default 20) caps new voicings that teachers' taps cause; it is not set on Cloud Run, so the default applies. Still unchecked: a real phone, WhatsApp opening the link, and the cap against the live server (tested offline only).
