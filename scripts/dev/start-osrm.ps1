# =============================================================================
# CivicBrain | scripts/dev/start-osrm.ps1 - starts OSRM (Docker) on 127.0.0.1:5000 and checks a route
#   pwsh -NoProfile -File scripts\dev\start-osrm.ps1
# Prepare the data once first: scripts\dev\prepare-osrm.ps1 (infra/osrm/README.md).
# =============================================================================
[CmdletBinding()]
param([int]$TimeoutSeconds = 60)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7

if (-not (Test-Path (Join-Path $RepoRoot 'infra\osrm\data\talegaon.osrm.mldgr'))) {
    throw 'OSRM data not prepared - run scripts\dev\prepare-osrm.ps1 -Pbf <file> first (infra/osrm/README.md).'
}
Write-Step 'docker compose up -d (infra/osrm)'
Invoke-Native -Exe 'docker' -Arguments @('compose', '-f', $OsrmCompose, 'up', '-d') -What 'docker compose up'

# depot D001 (18.729411, 73.699489) -> ward 1 test point (18.7440, 73.6760); OSRM wants lon,lat
$url = 'http://127.0.0.1:5000/route/v1/driving/73.699489,18.729411;73.6760,18.7440?overview=false'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$resp = $null
while ((Get-Date) -lt $deadline) {
    try { $resp = Invoke-RestMethod -Uri $url -TimeoutSec 5 -SkipHttpErrorCheck; break } catch { Start-Sleep -Seconds 2 }   # OSRM answers errors with HTTP 400 + code
}
if (-not $resp) { throw "OSRM did not answer within $TimeoutSeconds s. Check: docker compose -f infra\osrm\docker-compose.yml logs" }
if ($resp.code -ne 'Ok') { throw "OSRM answered code=$($resp.code) - is the extract covering Talegaon? (infra/osrm/README.md sec. 1)" }
$km = [math]::Round($resp.routes[0].distance / 1000, 2)
$min = [math]::Round($resp.routes[0].duration / 60, 1)
if ($km -le 0 -or $km -gt 30) { Write-Note "Route distance $km km looks wrong for Talegaon - check the extract bbox" }
Write-Ok "OSRM running: depot D001 -> ward 1 test point = $km km, $min min"
