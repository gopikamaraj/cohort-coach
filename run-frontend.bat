@echo off
rem Starts the web app (Vite) on http://localhost:5173. It sends /api calls to the API on port 8000,
rem so start run-backend.bat first. Stop with Ctrl+C.
cd /d "%~dp0apps\pwa"
if not exist "node_modules" (
  echo Installing web app dependencies first...
  call npm install
)
echo Web app: http://localhost:5173
call npm run dev
pause
