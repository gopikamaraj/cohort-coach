@echo off
rem Starts the Cohort Coach API on http://localhost:8000 (auto-reloads on code changes).
rem Reads settings from .env (AI_MODE, SPEECH_MODE, keys). Stop with Ctrl+C.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing. Run: python tasks.py setup
  pause
  exit /b 1
)
echo API:     http://localhost:8000   (health: http://localhost:8000/api/health)
echo Docs:    http://localhost:8000/docs
".venv\Scripts\python.exe" -m uvicorn services.api.main:app --reload --port 8000
pause
