@echo off
rem Opens the back end and the web app, each in its own window. There is one back end.
cd /d "%~dp0"
start "Cohort Coach back end" cmd /k "%~dp0run-backend.bat"
start "Cohort Coach web app" cmd /k "%~dp0run-frontend.bat"
echo Started. Open http://localhost:5173/#/roles when both windows say they are ready.
