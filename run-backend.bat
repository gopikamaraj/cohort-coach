@echo off
rem Starts the back end on http://localhost:8000 (auto-reloads on code changes). It is the only one:
rem the app, the papers and the demo all use it.
rem Reads keys from .env. Stop with Ctrl+C.
cd /d "%~dp0"
rem Local testing only: leaves the admin page open. A real server sets ADMIN_KEY instead.
set ADMIN_OPEN=1
set JUDGE_MODE=1
rem lesson audio is kept in .media-local\ on this machine (local only)
set MEDIA_LOCAL_STORE=1
rem Tester stats (first-run name sheet, Feedback button, Testing evidence). The team token tags your own devices.
set TESTER_STATS=1
if "%TESTER_TEAM_TOKEN%"=="" set TESTER_TEAM_TOKEN=local-team
set PWA_ORIGIN=http://localhost:5173
if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing. Run: python tasks.py setup
  pause
  exit /b 1
)
echo Back end: http://localhost:8000   (health: http://localhost:8000/api/health)
echo Docs:      http://localhost:8000/docs
".venv\Scripts\python.exe" -m uvicorn services.api.main:app --reload --port 8000
pause
