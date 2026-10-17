# Deploying staging (and later production)

Status: **recipe written, not yet run.** It needs hosting accounts and secrets (Gopi). Nothing below has been executed on a real host; steps marked "verify" are the checks to run once it is live. The defaults follow OD-3 in `docs/build/DECISIONS.md`: an always-on small API instance, managed Postgres, S3-compatible storage for published audio, and static hosting for the PWA. No plan that sleeps during 1–10 Nov.

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
