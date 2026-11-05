# Run Playwright specs in a visible browser with an on-screen overlay: the spec, test k of N and the progress %,
# each check with its expected value, and what was received when one fails.
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\e2e_watch.ps1 e2e/sync.spec.ts e2e/results.spec.ts
#   powershell -ExecutionPolicy Bypass -File scripts\e2e_watch.ps1 -SlowMo 400 e2e/app.spec.ts
# With no spec given, every spec runs. Do not start it while another Playwright run is going (same ports).
param([int]$SlowMo = 250, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Specs)
$pwa = Join-Path $PSScriptRoot "..\apps\pwa"
Set-Location $pwa
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'node|python' -and $_.CommandLine -match 'cohort-coach' -and $_.CommandLine -match 'playwright|uvicorn|vite' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Remove-Item "e2e*.sqlite*" -Force -ErrorAction SilentlyContinue
$list = & npx playwright test --list @Specs 2>$null | Where-Object { $_ -match '›' }
$env:E2E_TOTAL = [string]@($list).Count
$env:E2E_PROGRESS_FILE = Join-Path $env:TEMP "e2e_progress.txt"
Set-Content $env:E2E_PROGRESS_FILE ""
$env:E2E_OVERLAY = "1"
$env:E2E_SLOWMO = [string]$SlowMo
Write-Host "Running $($env:E2E_TOTAL) tests in a visible browser (slowMo $SlowMo ms)" -ForegroundColor Cyan
& npx playwright test --headed --workers=1 --reporter=list @Specs
