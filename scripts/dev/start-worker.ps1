# =============================================================================
# CivicBrain | scripts/dev/start-worker.ps1 - Python AI worker (claims jobs from PostgreSQL)
#   pwsh -NoProfile -File scripts\dev\start-worker.ps1
#   pwsh -NoProfile -File scripts\dev\start-worker.ps1 -WorkerId laptop1-worker2   # a second worker
#   pwsh -NoProfile -File scripts\dev\start-worker.ps1 -Database civicbrain_e2e     # used by start-e2e.ps1
# Entry point: ai-service\worker\run.py (python -m worker.run). Stop with Ctrl+C (graceful stop).
# =============================================================================
[CmdletBinding()]
param([string]$WorkerId, [string]$Database)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
if ($WorkerId) { $env:WORKER_ID = $WorkerId }
if ($Database) { $env:DB_NAME = $Database }
if ($env:DB_E2E_NAME -and $env:DB_NAME -eq $env:DB_E2E_NAME) { $env:STORAGE_ROOT = Join-Path $env:STORAGE_ROOT 'e2e' }   # same folder as the E2E backend
Assert-EnvKeys @('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_AI_USER', 'DB_AI_PASSWORD', 'WORKER_ID', 'STORAGE_ROOT',
    'OSRM_URL', 'YOLO_WEIGHTS', 'MODELS_DIR')
$ai = Join-Path $RepoRoot 'ai-service'
$py = Join-Path $ai '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw 'ai-service\.venv missing - see docs/10_SETUP_WINDOWS.md sec. 3' }
if (-not (Test-Path (Join-Path $ai 'worker\run.py'))) { throw 'ai-service\worker\run.py not found yet (built in P6).' }
if (-not (Test-PortOpen ([int]$env:DB_PORT) $env:DB_HOST)) { throw 'PostgreSQL is not reachable.' }
if ($env:ROUTING_MODE -eq 'osrm' -and -not (Test-PortOpen 5000)) { Write-Note 'OSRM is not running on 5000 - OPTIMIZE_PLAN jobs will fail and retry (start-osrm.ps1)' }
Write-Step "Worker $env:WORKER_ID on database $env:DB_NAME"
Invoke-Native -Exe $py -Arguments @('-m', 'worker.run') -WorkingDirectory $ai -What 'worker'
