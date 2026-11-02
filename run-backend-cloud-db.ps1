# Runs the LOCAL back end on http://localhost:8000 against the CLOUD database (Cloud SQL, database ccapp2).
# Everything the local app writes goes to the same database the live site uses: judges see it too.
#
# One-time: install the Cloud SQL Auth Proxy (https://cloud.google.com/sql/docs/postgres/sql-proxy), for example
#   winget install Google.CloudSQLProxy        (or download cloud-sql-proxy.x64.exe and put it on PATH)
# and run `gcloud auth login` once. The password is read from Secret Manager into this terminal's memory only:
# it is never written to .env or to any file.
#
# Use:  .\run-backend-cloud-db.ps1            (Ctrl+C to stop; the proxy stops with it)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$project  = "fln-cohort-coach"
$instance = "fln-cohort-coach:asia-south1:cohort-coach-db"
$database = "ccapp2"
$port     = 5433

$proxy = (Get-Command cloud-sql-proxy -ErrorAction SilentlyContinue)
if (-not $proxy) { $proxy = Get-Command cloud-sql-proxy.x64.exe -ErrorAction SilentlyContinue }
if (-not $proxy) { throw "cloud-sql-proxy is not installed. See the note at the top of this file." }

$pw = (gcloud secrets versions access latest --secret db-password --project $project).Trim()
if (-not $pw) { throw "Could not read the database password from Secret Manager (run: gcloud auth login)." }
$enc = [uri]::EscapeDataString($pw)
$env:DATABASE_URL = "postgresql+psycopg://postgres:$enc@127.0.0.1:$port/$database"
Remove-Variable pw, enc

$p = Start-Process -FilePath $proxy.Source -ArgumentList "$instance --port $port" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 4
try {
  # the same local settings run-backend.bat uses
  $env:ADMIN_OPEN = "1"; $env:JUDGE_MODE = "1"; $env:MEDIA_LOCAL_STORE = "1"
  $env:PWA_ORIGIN = "http://localhost:5173"
  Write-Host "Back end: http://localhost:8000  ->  CLOUD database '$database' (shared with the live site)"
  & ".venv\Scripts\python.exe" -m uvicorn services.api.main:app --reload --port 8000
} finally {
  if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id }
}
