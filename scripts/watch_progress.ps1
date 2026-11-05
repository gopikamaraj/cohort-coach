# Live status of the long background jobs (Playwright, pytest, vitest, servers) in one terminal.
# Run:  powershell -NoExit -File scripts\watch_progress.ps1   (refreshes every 5 s; Ctrl+C stops)
# It only reads: process list and the log files the runs write into %TEMP%. It changes nothing.
param([int]$Every = 5, [int]$Hours = 3)

$logs = $env:TEMP
$pattern = '^(e2e_|pytest|py_|vitest|phase3|suite_).*\.(txt|log)$'

function Age([datetime]$t) {
  $s = [int]((Get-Date) - $t).TotalSeconds
  if ($s -ge 3600) { return "{0}h{1:00}m" -f [int]($s / 3600), [int](($s % 3600) / 60) }
  if ($s -ge 60) { return "{0}m{1:00}s" -f [int]($s / 60), ($s % 60) }
  return "${s}s"
}

while ($true) {
  Clear-Host
  Write-Host ("Cohort Coach background jobs   {0}" -f (Get-Date -Format "HH:mm:ss")) -ForegroundColor Cyan
  Write-Host ("=" * 78)

  Write-Host "`nRunning now" -ForegroundColor Yellow
  $procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'cohort-coach' -and $_.CommandLine -match 'playwright|pytest|vitest|uvicorn|vite' -and $_.Name -match 'node|python'
  }
  if (-not $procs) { Write-Host "  nothing running" -ForegroundColor DarkGray }
  foreach ($p in $procs) {
    $what = if ($p.CommandLine -match 'playwright') { 'playwright' } elseif ($p.CommandLine -match 'pytest') { 'pytest' } elseif ($p.CommandLine -match 'vitest') { 'vitest' } elseif ($p.CommandLine -match 'uvicorn') { 'api server' } else { 'vite' }
    $up = if ($p.CreationDate) { Age $p.CreationDate } else { '?' }
    "  {0,-11} pid {1,-6} up {2,-8} {3}" -f $what, $p.ProcessId, $up, (($p.CommandLine -replace '\s+', ' ').Substring(0, [Math]::Min(48, $p.CommandLine.Length)))
  }

  Write-Host "`nRecent runs (logs in $logs)" -ForegroundColor Yellow
  $files = Get-ChildItem $logs -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $pattern -and $_.LastWriteTime -gt (Get-Date).AddHours(-$Hours) } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 6
  if (-not $files) { Write-Host "  no recent logs" -ForegroundColor DarkGray }
  foreach ($f in $files) {
    $text = Get-Content $f.FullName -Tail 4000 -ErrorAction SilentlyContinue
    $ok = @($text | Where-Object { $_ -match '^\s+ok\s+\d+' }).Count
    $bad = @($text | Where-Object { $_ -match '^\s+x\s+\d+' }).Count
    $final = $text | Where-Object { $_ -match '^\s+\d+ (passed|failed)|=+ .*(passed|failed).* =+|Tests\s+\d+' }
    $done = [bool]($text | Where-Object { $_ -match '^done' })
    $state = if ($done) { 'FINISHED' } elseif (((Get-Date) - $f.LastWriteTime).TotalSeconds -lt 120) { 'running ' } else { 'quiet   ' }
    $color = if ($done -and $bad -eq 0) { 'Green' } elseif ($bad -gt 0) { 'Red' } else { 'White' }
    Write-Host ("  {0}  {1,-22} ok {2,-4} fail {3,-3} updated {4} ago" -f $state, $f.Name, $ok, $bad, (Age $f.LastWriteTime)) -ForegroundColor $color
    $last = ($text | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1)
    if ($last) { Write-Host ("      last: {0}" -f $last.Trim().Substring(0, [Math]::Min(100, $last.Trim().Length))) -ForegroundColor DarkGray }
    foreach ($l in ($final | Select-Object -Last 3)) { Write-Host ("      {0}" -f $l.Trim()) -ForegroundColor Gray }
    foreach ($l in ($text | Where-Object { $_ -match '^\s+x\s+\d+' } | Select-Object -Last 5)) { Write-Host ("      FAIL {0}" -f $l.Trim().Substring(0, [Math]::Min(90, $l.Trim().Length))) -ForegroundColor Red }
  }

  Write-Host "`nRefreshing every ${Every}s. Ctrl+C to stop." -ForegroundColor DarkGray
  Start-Sleep -Seconds $Every
}
