# =============================================================================
# CivicBrain | scripts/dev/start-tunnel.ps1 - Cloudflare quick tunnel = HTTPS URL for phones
# Phones need HTTPS for camera, GPS and device orientation. A quick tunnel needs no account.
#   pwsh -NoProfile -File scripts\dev\start-tunnel.ps1          # dev: tunnel to Vite :5173
#   pwsh -NoProfile -File scripts\dev\start-tunnel.ps1 -Demo    # demo: tunnel to Spring :8080 (built SPA)
#   pwsh -NoProfile -File scripts\dev\start-tunnel.ps1 -UrlFile logs\run\tunnel_url.txt   (used by start-all.ps1 -Tunnel)
# Easiest: scripts\dev\start-all.ps1 -Tunnel starts the tunnel FIRST and passes the URL to the backend
# (-BaseUrl), so .env never has to be edited. Started alone: set APP_BASE_URL=<that URL> in .env and restart
# the backend (links in e-mails/WhatsApp and the refresh Origin check use it). The URL changes every run.
# Anyone with the URL can open the site: stop the tunnel (Ctrl+C) when you are done. HUMAN-only script.
# =============================================================================
[CmdletBinding()]
param([switch]$Demo, [string]$UrlFile)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
$port = if ($Demo) { 8080 } else { 5173 }
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) { throw 'cloudflared not found - winget install Cloudflare.cloudflared' }
if (-not $UrlFile -and -not (Test-PortOpen $port)) { throw "Nothing is listening on port $port - start the $(if ($Demo) {'backend'} else {'frontend'}) first." }

Write-Step "Quick tunnel -> http://localhost:$port  (Ctrl+C to stop)"
$shown = $false
$oldEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'   # cloudflared logs to stderr
try {
    & $cf.Source tunnel --no-autoupdate --url "http://localhost:$port" 2>&1 | ForEach-Object {
        $line = "$_"
        if (-not $shown -and $line -match '(https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com)') {
            $shown = $true
            $u = $Matches[1]
            Write-Host ''
            Write-Host "  PUBLIC URL: $u" -ForegroundColor Green
            if ($UrlFile) {
                Set-Content -LiteralPath $UrlFile -Value $u -Encoding ascii -NoNewline
                Write-Host '  start-all.ps1 passes this URL to the backend (nothing to edit).' -ForegroundColor Green
            } else {
                Write-Host "  1. In .env set  APP_BASE_URL=$u   and restart start-backend.ps1" -ForegroundColor Green
            }
            Write-Host '  Open the URL on the phone in Chrome (Android) or Safari (iPhone); allow camera + location' -ForegroundColor Green
            Write-Host ''
        } elseif ($line -match 'ERR|error') { Write-Host $line -ForegroundColor Yellow }
    }
} finally { $ErrorActionPreference = $oldEap }
