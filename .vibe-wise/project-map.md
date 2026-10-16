# Project Map

## Purpose
Cohort Coach groups primary teachers for training by the specific error their Grade 3 pupils make, gives them 3-week voice tracks on Telegram, and lets them rehearse in a simulated Practice Class (CLAUDE.md §1).

## Requirements
Defined in CLAUDE.md and docs/build/BUILD_PROMPTS.md: code computes every number, child privacy, teacher dignity, AI output gated before teachers, simulated data labelled. Deadline: submit 31 Oct 2026.

## Components
Verified present (P00 skeleton only):
- services/api/main.py: FastAPI app (health route; tests/test_health.py)
- apps/pwa/: React + Vite + TS shell (src/App.tsx, src/strings.ts)
- tasks.py: cross-platform task runner
- .github/workflows/ci.yml: CI
- Empty packages awaiting phases: engine/, ai/ (calls, guard, validators, prompts), content/, evals/, services/speech/, services/api/channels/{telegram,whatsapp}, data/synthetic/
- Docs: docs/build/ (PROGRESS, DECISIONS, BUILD_PROMPTS), docs/design/

## Main Flow
Planned in CLAUDE.md (not yet implemented):
teacher check -> engine diagnosis -> cohort/track -> Telegram lessons + Practice Class -> next check -> evaluation.
Implemented so far: API health route and PWA shell only.

## Data and Trust Boundaries
Planned: per-child answers only in phone IndexedDB; server stores class-level counts; Postgres in production, SQLite locally. Not yet implemented.

## Build and Deployment
`python tasks.py setup | dev | test | check` (tasks.py). CI in .github/workflows/ci.yml.

## Unknowns
Everything beyond P00: engine design (P01), AI client, deployment host, storage models.
