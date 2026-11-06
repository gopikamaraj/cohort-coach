# Runs the LOCAL back end on http://localhost:8000 against the CLOUD database (Cloud SQL, database ccapp2).
# Everything the local app writes goes to the same database the live site uses: judges see it too.
#
# One-time: install the Cloud SQL Auth Proxy (https://cloud.google.com/sql/docs/postgres/sql-proxy), for example
#   winget install Google.CloudSQLProxy        (or download cloud-sql-proxy.x64.exe and put it on PATH)
# and run `gcloud auth login` once. The password is read from Secret Manager into this terminal's memory only:
# it is never written to .env or to any file.
#
# Use:  .\run-backend-cloud-db.ps1            (Ctrl+C to stop; the proxy stops with it)

param([switch]$Clear, [string]$Script = "", [string[]]$ScriptArgs = @())   # -Script: run scripts\<name> against the cloud database, then stop   # -Clear: delete every row of the cloud database (asks you to type its name), then stop
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$project  = "fln-cohort-coach"
$instance = "fln-cohort-coach:asia-south1:cohort-coach-db"
$database = "ccapp2"
$port     = 5433

$already = [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
$proxy = (Get-Command cloud-sql-proxy -ErrorAction SilentlyContinue)
if (-not $proxy) { $proxy = Get-Command cloud-sql-proxy.x64.exe -ErrorAction SilentlyContinue }
if (-not $proxy -and (Test-Path "C:\tools\cloud-sql-proxy.exe")) { $proxy = Get-Item "C:\tools\cloud-sql-proxy.exe"; $proxy | Add-Member -NotePropertyName Source -NotePropertyValue $proxy.FullName -Force }
if (-not $proxy -and -not $already) { throw "cloud-sql-proxy is not installed. See the note at the top of this file." }

$pw = (gcloud secrets versions access latest --secret db-password --project $project).Trim()
if (-not $pw) { throw "Could not read the database password from Secret Manager (run: gcloud auth login)." }
$enc = [uri]::EscapeDataString($pw)
$env:DATABASE_URL = "postgresql+psycopg://postgres:$enc@127.0.0.1:$port/$database"
Remove-Variable pw, enc

$p = $null
if ($already) { Write-Host "Using the proxy already running on port $port." }
else {
  $p = Start-Process -FilePath $proxy.Source -ArgumentList "$instance --port $port" -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 4
}
try {
  if ($Clear) {
    & ".venv\Scripts\python.exe" scripts\clear_all_rows.py
    return
  }
  if ($Script) {
    & ".venv\Scripts\python.exe" "scripts\$Script" @ScriptArgs
    return
  }
  # the same local settings run-backend.bat uses
  $env:ADMIN_OPEN = "1"; $env:OFFICER_MIN_CLASSES = "2"; $env:JUDGE_MODE = "1"; $env:MEDIA_LOCAL_STORE = "1"
  $env:TESTER_STATS = "1"; if (-not $env:TESTER_TEAM_TOKEN) { $env:TESTER_TEAM_TOKEN = "local-team" }   # Testing evidence and the Feedback button, as run-backend.bat does
  $env:PWA_ORIGIN = "http://localhost:5173"
  Write-Host "Back end: http://localhost:8000  ->  CLOUD database '$database' (shared with the live site)"
  & ".venv\Scripts\python.exe" -m uvicorn services.api.main:app --reload --port 8000
} finally {
  if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id }
}
