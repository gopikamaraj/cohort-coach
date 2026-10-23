@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if "%VERCEL_TOKEN%"=="" (
  echo Set VERCEL_TOKEN first 1>&2
  exit /b 1
)

echo == Tests ==
pushd backend
python -m pytest -q
if errorlevel 1 goto :fail
popd

pushd frontend
call npm ci --silent
if errorlevel 1 goto :fail
call npm test --if-present -- --run
if errorlevel 1 goto :fail
popd

echo == Backend preview ==
pushd backend
set "BACKEND_URL="
for /f "delims=" %%i in ('vercel deploy -y') do set "BACKEND_URL=%%i"
popd
if not defined BACKEND_URL goto :fail
echo %BACKEND_URL%

echo == Frontend preview ==
pushd frontend
set "FRONTEND_URL="
for /f "delims=" %%i in ('vercel deploy -y -b VITE_API_URL=%BACKEND_URL%') do set "FRONTEND_URL=%%i"
popd
if not defined FRONTEND_URL goto :fail

echo == Health check ==
pushd backend
call vercel curl /health --deployment %BACKEND_URL%
set "HC=%errorlevel%"
popd

echo.
echo BACKEND:  %BACKEND_URL%
echo FRONTEND: %FRONTEND_URL%
if not "%HC%"=="0" echo WARNING: health check failed
exit /b %HC%

:fail
echo DEPLOY FAILED 1>&2
exit /b 1