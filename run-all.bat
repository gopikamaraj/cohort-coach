@echo off
rem Opens the back end and the web app, each in its own window. There is one back end.
rem   run-all.bat          back end on the LOCAL database (dev.sqlite)
rem   run-all.bat cloud    back end on the CLOUD database (same data as the live site) through the
rem                        Cloud SQL proxy; see run-backend-cloud-db.ps1 for the one-time setup
cd /d "%~dp0"
if /i "%~1"=="cloud" (
  start "Cohort Coach back end (CLOUD database)" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0run-backend-cloud-db.ps1"
) else (
  start "Cohort Coach back end" cmd /k "%~dp0run-backend.bat"
)
start "Cohort Coach web app" cmd /k "%~dp0run-frontend.bat"
echo Started. Open http://localhost:5173/#/roles when both windows say they are ready.
