@echo off
rem Opens the back end and the web app, each in its own window. There is one back end.
rem   run-all.bat          back end on the CLOUD database (the same data as the live site), through the
rem                        Cloud SQL proxy; see run-backend-cloud-db.ps1. Start run_clound_proxy.ps1 first, or
rem                        let the script start the proxy itself.
rem   run-all.bat local    back end on the LOCAL database (dev.sqlite), as before
cd /d "%~dp0"
if /i "%~1"=="local" (
  start "Cohort Coach back end (local database)" cmd /k "%~dp0run-backend.bat"
) else (
  start "Cohort Coach back end (CLOUD database)" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0run-backend-cloud-db.ps1"
)
start "Cohort Coach web app" cmd /k "%~dp0run-frontend.bat"
echo Started. Open http://localhost:5173/#/roles when both windows say they are ready.
