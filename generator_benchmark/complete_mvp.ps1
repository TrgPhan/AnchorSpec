param([Parameter(Mandatory=$true)][string]$Release, [int]$WaitPid = 0)
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\Ad\Downloads\DENSO\generator_benchmark'
if ($WaitPid -gt 0) {
    $p = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
    if ($p) { Wait-Process -Id $WaitPid -Timeout 3600 }
}
if (-not (Test-Path (Join-Path $Release 'FROZEN.json'))) { throw 'Development did not freeze; inspect logs. Final must not run.' }
python (Join-Path $Root 'mvp_run.py') finalize --output $Release
if ($LASTEXITCODE -ne 0) { throw 'Finalization failed. Evidence retained.' }
python (Join-Path $Root 'mvp_run.py') report --output $Release
if ($LASTEXITCODE -ne 0) { throw 'Report/acceptance failed. Evidence retained.' }
python (Join-Path $Root 'mvp_cli.py') verify --release $Release
if ($LASTEXITCODE -ne 0) { throw 'Integrity failed.' }
Write-Output 'MVP EXECUTION COMPLETE; inspect research gates in final/summary.json.'