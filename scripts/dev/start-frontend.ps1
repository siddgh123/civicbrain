# =============================================================================
# CivicBrain | scripts/dev/start-frontend.ps1 - Vite dev server on http://localhost:5173
# /api is proxied to http://localhost:8080 (vite.config.ts). No secrets are needed here.
#   pwsh -NoProfile -File scripts\dev\start-frontend.ps1
# Phones: run start-tunnel.ps1 in another window (vite.config.ts must allow '.trycloudflare.com').
# =============================================================================
[CmdletBinding()]
param()
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
$fe = Join-Path $RepoRoot 'frontend'
if (-not (Test-Path (Join-Path $fe 'package.json'))) { throw 'frontend\package.json not found (created in P0).' }
if (-not (Test-Path (Join-Path $fe 'node_modules'))) { throw 'frontend\node_modules missing - run: cd frontend; npm install' }
if (Test-PortOpen 5173) { throw 'Port 5173 is already in use - is Vite already running?' }
if (-not (Test-PortOpen 8080)) { Write-Note 'Backend is not running on 8080 - API calls will fail until you start start-backend.ps1' }
Write-Step 'Frontend: http://localhost:5173'
$npm = if ($IsWindows) { 'npm.cmd' } else { 'npm' }
Invoke-Native -Exe $npm -Arguments @('run', 'dev', '--', '--port', '5173', '--strictPort') -WorkingDirectory $fe -What 'vite'
