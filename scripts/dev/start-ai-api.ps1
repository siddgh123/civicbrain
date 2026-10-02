# =============================================================================
# CivicBrain | scripts/dev/start-ai-api.ps1 - small FastAPI (health, models, admin requeue)
# Binds to 127.0.0.1:8001 ONLY (never 0.0.0.0).
#   pwsh -NoProfile -File scripts\dev\start-ai-api.ps1
# =============================================================================
[CmdletBinding()]
param([string]$Database)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
if ($Database) { $env:DB_NAME = $Database }
if ($env:DB_E2E_NAME -and $env:DB_NAME -eq $env:DB_E2E_NAME) { $env:STORAGE_ROOT = Join-Path $env:STORAGE_ROOT 'e2e' }   # same folder as the E2E backend
Assert-EnvKeys @('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_AI_USER', 'DB_AI_PASSWORD', 'AI_SERVICE_JWT_SECRET', 'AI_API_HOST', 'AI_API_PORT', 'MODELS_DIR')
if ($env:AI_API_HOST -ne '127.0.0.1') { throw "AI_API_HOST must be 127.0.0.1 (found $env:AI_API_HOST) - docs/07_SECURITY.md sec. 5" }
$ai = Join-Path $RepoRoot 'ai-service'
$py = Join-Path $ai '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw 'ai-service\.venv missing - see docs/10_SETUP_WINDOWS.md sec. 3' }
if (-not (Test-Path (Join-Path $ai 'app\main.py'))) { throw 'ai-service\app\main.py not found yet (created in P0).' }
if (Test-PortOpen ([int]$env:AI_API_PORT)) { throw "Port $env:AI_API_PORT is already in use." }
Write-Step "AI API: http://$($env:AI_API_HOST):$($env:AI_API_PORT)/health"
Invoke-Native -Exe $py -Arguments @('-m', 'uvicorn', 'app.main:app', '--host', $env:AI_API_HOST, '--port', $env:AI_API_PORT, '--no-server-header') -WorkingDirectory $ai -What 'uvicorn'
