@echo off
rem Starts the web app (Vite) on http://localhost:5173. Every call goes to the one back end on 8000:
rem start run-backend.bat first. Stop with Ctrl+C.
cd /d "%~dp0apps\pwa"
set VITE_PILOT_MODE=
set VITE_API_BASE=http://localhost:8000
if not exist "node_modules" (
  echo Installing web app dependencies first...
  call npm install
)
echo Web app: http://localhost:5173   (landing: http://localhost:5173/#/roles)
call npm run dev
pause
