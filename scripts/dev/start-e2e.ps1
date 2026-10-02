# =============================================================================
# CivicBrain | scripts/dev/start-e2e.ps1 - starts the full stack against civicbrain_e2e for Playwright
#   pwsh -NoProfile -File scripts\dev\start-e2e.ps1          # seed + start services in new windows
#   pwsh -NoProfile -File scripts\dev\start-e2e.ps1 -NoSeed  # keep current E2E data
# Then:  cd frontend; npx playwright test   (Playwright starts Vite itself via webServer)
# Stop: close the windows (Ctrl+C in each). Do not run the dev stack at the same time (same ports).
# =============================================================================
[CmdletBinding()]
param([switch]$NoSeed, [int]$TimeoutSeconds = 120)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
$db = $env:DB_E2E_NAME
Assert-DisposableDatabase $db
foreach ($p in 8080, 8001) { if (Test-PortOpen $p) { throw "Port $p is in use - stop the dev services first." } }

if (-not $NoSeed) { & (Join-Path $PSScriptRoot 'seed-e2e.ps1'); if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'seed-e2e failed' } }

$pwsh = (Get-Process -Id $PID).Path
function Start-Window([string]$Title, [string]$Script, [string[]]$ScriptArgs) {
    $argList = @('-NoExit', '-NoProfile', '-Command', "`$host.UI.RawUI.WindowTitle = '$Title'; & '$(Join-Path $PSScriptRoot $Script)' $($ScriptArgs -join ' ')")
    Start-Process -FilePath $pwsh -ArgumentList $argList -WorkingDirectory $RepoRoot | Out-Null
    Write-Step "started window: $Title"
}
if (-not ((Test-PortOpen 1025) -and (Test-PortOpen 8025))) { Start-Window 'CB e2e mailpit' 'start-mailpit.ps1' @() }
Start-Window 'CB e2e backend' 'start-backend.ps1' @('-Database', $db, '-SpringProfile', 'e2e')
Start-Window 'CB e2e ai-api' 'start-ai-api.ps1' @('-Database', $db)
Start-Window 'CB e2e worker' 'start-worker.ps1' @('-Database', $db, '-WorkerId', 'e2e-worker')
if ($env:ROUTING_MODE -eq 'osrm' -and -not (Test-PortOpen 5000)) { Write-Note 'OSRM is not running - E2E-03 (plan generation) will fail. Start it: scripts\dev\start-osrm.ps1' }

Write-Step "Waiting for health endpoints (max $TimeoutSeconds s)"
$checks = [ordered]@{
    'backend /actuator/health' = 'http://127.0.0.1:8080/actuator/health'
    'AI API /health'           = "http://127.0.0.1:$($env:AI_API_PORT)/health"
    'Mailpit'                  = 'http://127.0.0.1:8025/api/v1/info'
}
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$pending = [System.Collections.Generic.List[string]]::new([string[]]$checks.Keys)
while ($pending.Count -gt 0 -and (Get-Date) -lt $deadline) {
    foreach ($name in @($pending)) {
        try { $r = Invoke-WebRequest -Uri $checks[$name] -TimeoutSec 3 -SkipHttpErrorCheck; if ($r.StatusCode -eq 200) { Write-Ok $name; [void]$pending.Remove($name) } } catch { }
    }
    if ($pending.Count) { Start-Sleep -Seconds 3 }
}
if ($pending.Count) { Write-Bad "Not healthy: $($pending -join ', ') - look at the service windows"; exit 1 }
Write-Ok 'E2E stack is up. Run:  cd frontend; npx playwright test'
