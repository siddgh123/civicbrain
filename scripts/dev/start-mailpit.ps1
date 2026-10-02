# =============================================================================
# CivicBrain | scripts/dev/start-mailpit.ps1 - local fake mail server for dev and E2E
#   SMTP  127.0.0.1:1025  (the backend sends here: SMTP_HOST=localhost, SMTP_PORT=1025)
#   Web   http://localhost:8025  (read OTP and notification mails; E2E uses its /api/v1/messages)
#   pwsh -NoProfile -File scripts\dev\start-mailpit.ps1
# Uses mailpit.exe from PATH or tools\mailpit\mailpit.exe (GitHub release 1.31.x); otherwise Docker.
# =============================================================================
[CmdletBinding()]
param([switch]$Docker)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
$image = 'axllent/mailpit:v1.31.3'

if ((Test-PortOpen 1025) -or (Test-PortOpen 8025)) {
    if ((Test-PortOpen 1025) -and (Test-PortOpen 8025)) { Write-Ok 'Mailpit already running: http://localhost:8025'; exit 0 }
    throw 'Port 1025 or 8025 is used by another program.'
}

$exe = $null
if (-not $Docker) {
    $cmd = Get-Command mailpit -ErrorAction SilentlyContinue
    if ($cmd) { $exe = $cmd.Source }
    elseif (Test-Path (Join-Path $RepoRoot 'tools\mailpit\mailpit.exe')) { $exe = Join-Path $RepoRoot 'tools\mailpit\mailpit.exe' }
}

if ($exe) {
    Write-Step "Mailpit ($exe): SMTP 127.0.0.1:1025, UI http://localhost:8025  (Ctrl+C to stop)"
    # --max 5000 keeps the inbox small; bind to localhost only
    Invoke-Native -Exe $exe -Arguments @('--smtp', '127.0.0.1:1025', '--listen', '127.0.0.1:8025', '--max', '5000') -What 'mailpit'
} else {
    Write-Step "mailpit.exe not found - using Docker image $image"
    $oldEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $existing = & docker ps -a --filter 'name=^civicbrain-mailpit$' --format '{{.Names}}' 2>$null
    $ErrorActionPreference = $oldEap
    if ($existing -eq 'civicbrain-mailpit') {
        Invoke-Native -Exe 'docker' -Arguments @('start', 'civicbrain-mailpit') -What 'docker start'
    } else {
        Invoke-Native -Exe 'docker' -Arguments @('run', '-d', '--name', 'civicbrain-mailpit', '-p', '127.0.0.1:1025:1025',
            '-p', '127.0.0.1:8025:8025', '--restart', 'unless-stopped', $image) -What 'docker run mailpit'
    }
    Start-Sleep -Seconds 2
    if (Test-PortOpen 8025) { Write-Ok 'Mailpit running in Docker: http://localhost:8025' } else { throw 'Mailpit container did not start - docker logs civicbrain-mailpit' }
}
