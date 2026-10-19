@echo off
rem Opens the backend and the frontend, each in its own window.
cd /d "%~dp0"
start "Cohort Coach API" cmd /k "%~dp0run-backend.bat"
start "Cohort Coach web app" cmd /k "%~dp0run-frontend.bat"
echo Started. Open http://localhost:5173 when both windows say they are ready.
