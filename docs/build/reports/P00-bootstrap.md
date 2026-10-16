# P00 · Bootstrap — report

**Status:** ✅ done. CI green on `83e571b` (GitHub Actions run 38881893876). The first run failed only in the gitleaks action (commit-range error, not a leak); replaced by the gitleaks CLI over full history.

## Built
Repo skeleton per CLAUDE.md §6, `pyproject.toml` + `requirements.lock`, FastAPI `/api/health`, Vite/React/TS PWA shell (judge-mode placeholder in a phone frame, en/hi/ta strings), `tasks.py` (all §10 commands; later phases print `available after PXX`), `.env.example`, MIT licence, CI workflow, docs skeleton, `scripts/feedback_table.py`.

## Inventory
Working directory held docs, `.claude` agents/skills and an empty `.venv`; no code. Finguru: no paths given, so voice and Telegram are built fresh (DECISIONS.md). Toolchain: Python 3.12.7, Node 24.19.0, npm 11.17.0, git 2.46.0, gh 2.97.0. Missing: `uv` (optional, venv+pip fallback used), `ffmpeg` (needed from P07).

## Acceptance
See `docs/build/tasks/P00.md`. Evidence run 2026-10-16: pytest 10 passed; vitest 2 passed; ruff, mypy --strict, eslint, tsc clean; `GET /api/health` → `{"status":"ok","version":"0.1.0"}`; PWA dev page HTTP 200; `vite build` precache 216 KiB.

## AI calls touched
None.

## Deviations
- Playwright installed as a dev dependency only; browsers not downloaded until P06.
- `setup` and `dev` were re-run through `tasks.py` after review; both worked (setup on the existing venv, not a fresh one).
- `.gitignore` widened to all of `data/pilot/`; CI badge is a placeholder until a remote exists.
- Pre-commit hook runs the full `check`, which will slow commits; remove if it gets in the way.

## TODO-HUMAN
Gopi (open): Telegram reuse paths (optional); ffmpeg; Sarvam key. Done: voice uses Sarvam directly (DECISIONS); GitHub remote and CI proof.

## Judged area served
Repo quality (README, CI, tooling). No evidence numbers yet.
