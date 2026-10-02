# =============================================================================
# CivicBrain | scripts/dev/start-all.ps1 - starts / restarts / stops the whole local stack on ONE laptop
# Every service runs in its own (minimised) window; its output also goes to logs\<service>.log.
# The script itself returns as soon as everything is healthy, so the Antigravity agent may run it
# (allow list in docs/10_SETUP_WINDOWS.md sec. 5) - EXCEPT -Tunnel, which only a human uses.
#
#   pwsh -NoProfile -File scripts\dev\start-all.ps1                         # dev stack (database DB_NAME)
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend -Restart  # after backend code changes
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only worker,ai-api -Restart   # after AI code changes
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E -Restart           # same services on civicbrain_e2e
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status                 # what runs, healthy or not
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop                   # stop everything it started
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Tunnel                 # HUMAN: + HTTPS URL for phones
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -Demo -Tunnel           # HUMAN, demo day: jar with SPA + tunnel
#   pwsh -NoProfile -File scripts\dev\start-all.ps1 -SelfTest               # run twice (two separate commands): checks
#                                                   that windows started by the agent survive its terminal (P01)
#
# Services: mailpit (SMTP 1025 / UI 8025), ai-api (127.0.0.1:8001), worker, frontend (Vite 5173), backend (8080).
# Dev and E2E use the same ports, so only one stack runs at a time (-E2E/-Demo need -Restart if dev runs).
# Frontend code needs no restart (Vite reloads); backend and Python code do.
# Logs are appended (each start writes a '===== <time> start <service> mode=<mode> =====' header line).
# Process ids are kept in logs\run\<service>.json; -Stop/-Restart only stop processes this script
# started (process id + start time must match), together with their child processes.
# Never prints secrets (the child scripts load .env themselves).
# =============================================================================
[CmdletBinding()]
param(
    [string[]]$Only,   # mailpit|ai-api|worker|frontend|backend|tunnel ('tunnel' only with -Stop); 'a,b' or a b both work
    [switch]$Restart,
    [switch]$Stop,
    [switch]$Status,
    [switch]$E2E,
    [switch]$Demo,
    [switch]$Tunnel,
    [switch]$SelfTest,
    [int]$TimeoutSec = 300
)
# KIT-FIX: pwsh -File passes "worker,ai-api" as ONE string -> split + validate by hand (ValidateSet rejected it)
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$badOnly = @($Only | Where-Object { $_ -notin 'mailpit', 'ai-api', 'worker', 'frontend', 'backend', 'tunnel' })
if ($badOnly.Count) { throw "Unknown -Only value(s): $($badOnly -join ', '). Allowed: mailpit, ai-api, worker, frontend, backend, tunnel" }
if (-not $Only.Count) { $Only = $null }
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
if (-not $IsWindows) { throw 'start-all.ps1 runs on Windows only.' }
if ($E2E -and $Demo) { throw 'Use either -E2E or -Demo.' }
if ($E2E -and $Tunnel) { throw '-Tunnel is for the dev or demo stack, not -E2E.' }

$cfg = Import-DotEnv -NoProcessEnv           # values are only read here, never printed
function Get-Cfg([string]$Key, [string]$Default = '') { if ($cfg.Contains($Key) -and $cfg[$Key]) { [string]$cfg[$Key] } else { $Default } }
$mode = if ($E2E) { 'e2e' } elseif ($Demo) { 'demo' } else { 'dev' }
$e2eDb = Get-Cfg 'DB_E2E_NAME' 'civicbrain_e2e'
$aiPort = [int](Get-Cfg 'AI_API_PORT' '8001')
$dbHost = Get-Cfg 'DB_HOST' 'localhost'
$dbPort = [int](Get-Cfg 'DB_PORT' '5432')
$useMailpit = ((Get-Cfg 'SMTP_PORT') -eq '1025')

$logDir = Join-Path $RepoRoot 'logs'
$runDir = Join-Path $logDir 'run'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$pwshExe = (Get-Process -Id $PID).Path

# ---------- service table ----------
$all = [ordered]@{
    'mailpit'  = @{ Script = 'start-mailpit.ps1'; Args = @(); Health = 'mailpit' }
    'ai-api'   = @{ Script = 'start-ai-api.ps1'; Args = @(); Health = "http://127.0.0.1:$aiPort/health" }
    'worker'   = @{ Script = 'start-worker.ps1'; Args = @(); Health = 'alive' }
    'frontend' = @{ Script = 'start-frontend.ps1'; Args = @(); Health = 'port:5173' }
    'backend'  = @{ Script = 'start-backend.ps1'; Args = @(); Health = 'http://127.0.0.1:8080/actuator/health' }
}
if ($E2E) {
    $all['ai-api'].Args = @('-Database', $e2eDb)
    $all['worker'].Args = @('-Database', $e2eDb, '-WorkerId', 'e2e-worker')
    $all['backend'].Args = @('-Database', $e2eDb, '-SpringProfile', 'e2e')
}
if ($Demo) { $all.Remove('frontend'); $all['backend'].Args = @('-Prod') }
if (-not $useMailpit -and -not $E2E) { $all.Remove('mailpit') }   # real SMTP (Gmail) in .env; E2E always uses Mailpit
$names = if ($Only) { @($Only | Where-Object { $all.Contains($_) }) } else { @($all.Keys) }
# components that are not built yet are skipped (the prompts build them one by one); asked for with -Only -> error later
$present = @{
    'ai-api'   = (Test-Path -LiteralPath (Join-Path $RepoRoot 'ai-service\app\main.py'))
    'worker'   = (Test-Path -LiteralPath (Join-Path $RepoRoot 'ai-service\worker\run.py'))
    'frontend' = (Test-Path -LiteralPath (Join-Path $RepoRoot 'frontend\node_modules'))
    'backend'  = (Test-Path -LiteralPath (Join-Path $RepoRoot 'backend\mvnw.cmd'))
    'mailpit'  = $true
}
if (-not $Only) {
    $missing = @($names | Where-Object { -not $present[$_] })
    if ($missing.Count) { Write-Note "not built yet, skipped: $($missing -join ', ')" }
    $names = @($names | Where-Object { $present[$_] })
}

# ---------- helpers ----------
function Get-RunInfo([string]$Name) {
    $f = Join-Path $runDir "$Name.json"
    if (-not (Test-Path -LiteralPath $f)) { return $null }
    try { $i = Get-Content -Raw -LiteralPath $f | ConvertFrom-Json } catch { return $null }
    if (-not $i -or -not $i.pid) { return $null }
    $p = Get-Process -Id ([int]$i.pid) -ErrorAction SilentlyContinue
    if ($p -and $p.StartTime.ToUniversalTime().Ticks -eq [long]$i.startTicks) { $i | Add-Member -NotePropertyName alive -NotePropertyValue $true -Force }
    else { $i | Add-Member -NotePropertyName alive -NotePropertyValue $false -Force }
    return $i
}
function Save-RunInfo([string]$Name, [hashtable]$Info) {
    $Info | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDir "$Name.json") -Encoding utf8
}
function Test-Healthy([string]$Name) {
    $h = $all[$Name].Health
    switch -Regex ($h) {
        '^mailpit$' { return ((Test-PortOpen 1025) -and (Test-PortOpen 8025)) }
        '^port:(\d+)$' { return (Test-PortOpen ([int]$Matches[1])) }
        '^alive$' { $i = Get-RunInfo $Name; return [bool]($i -and $i.alive) }
        '^http' {
            try { $r = Invoke-WebRequest -Uri $h -TimeoutSec 3 -SkipHttpErrorCheck; return ($r.StatusCode -eq 200) } catch { return $false }
        }
    }
    return $false
}
function Get-ServicePort([string]$Name) {
    $ports = @{ 'backend' = 8080; 'frontend' = 5173; 'ai-api' = $aiPort; 'mailpit' = 8025 }
    if ($ports.ContainsKey($Name)) { return [int]$ports[$Name] }
    return 0
}
function Show-LogTail([string]$Name, [int]$Lines = 20) {
    $log = Join-Path $logDir "$Name.log"
    if (Test-Path -LiteralPath $log) {
        Write-Host "---- last $Lines lines of logs\$Name.log ----" -ForegroundColor Yellow
        Get-Content -LiteralPath $log -Tail $Lines | ForEach-Object { Write-Host "  $_" }
    }
}
function Stop-Service2([string]$Name) {
    $i = Get-RunInfo $Name
    if (-not $i -or -not $i.alive) { return $false }
    & taskkill.exe /PID ([int]$i.pid) /T /F *> $null       # the window process and its children (java, node, python)
    Save-RunInfo $Name @{ name = $Name; pid = 0; startTicks = '0'; mode = $i.mode; stoppedAt = (Get-Date).ToString('s') }
    $port = Get-ServicePort $Name
    if ($port) {
        $until = (Get-Date).AddSeconds(30)
        while ((Test-PortOpen $port) -and (Get-Date) -lt $until) { Start-Sleep -Milliseconds 500 }
        if (Test-PortOpen $port) { Write-Note "$Name stopped, but port $port is still in use (another program?)" }
    }
    Write-Ok "stopped $Name"
    return $true
}
function ConvertTo-PsLiteral([string]$s) { "'" + $s.Replace("'", "''") + "'" }
function Start-Service2([string]$Name, [string[]]$ExtraArgs = @()) {
    $svc = $all[$Name]
    $log = Join-Path $logDir "$Name.log"
    $argList = @(@($svc.Args) + @($ExtraArgs) | Where-Object { $null -ne $_ -and "$_" -ne '' })   # never pass empty arguments
    $argText = ($argList | ForEach-Object { if ($_ -like '-*') { $_ } else { ConvertTo-PsLiteral $_ } }) -join ' '
    $inner = if ($svc.Contains('Command')) { $svc.Command } else { "& $(ConvertTo-PsLiteral (Join-Path $PSScriptRoot $svc.Script)) $argText" }
    $cmd = @"
`$ErrorActionPreference = 'Continue'
`$host.UI.RawUI.WindowTitle = 'CivicBrain $Name ($mode)'
`$env:CB_MERGE_STDERR = '1'; `$env:PYTHONUNBUFFERED = '1'; `$env:NO_COLOR = '1'
"===== `$(Get-Date -Format 's') start $Name mode=$mode =====" | Out-File -FilePath $(ConvertTo-PsLiteral $log) -Append -Encoding utf8
try { $inner *>&1 | Tee-Object -FilePath $(ConvertTo-PsLiteral $log) -Append }
catch { "FATAL: `$(`$_.Exception.Message)" | Tee-Object -FilePath $(ConvertTo-PsLiteral $log) -Append }
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
    $p = Start-Process -FilePath $pwshExe -ArgumentList @('-NoProfile', '-EncodedCommand', $encoded) `
        -WorkingDirectory $RepoRoot -WindowStyle Minimized -PassThru
    Save-RunInfo $Name @{ name = $Name; pid = $p.Id; startTicks = [string]$p.StartTime.ToUniversalTime().Ticks; mode = $mode
        log = "logs\$Name.log"; startedAt = (Get-Date).ToString('s') }
    Write-Step "started $Name ($mode) - window 'CivicBrain $Name', log logs\$Name.log"
}
function Wait-Healthy([string]$Name, [int]$Seconds) {
    $until = (Get-Date).AddSeconds($Seconds)
    $minAlive = if ($all[$Name].Health -eq 'alive') { (Get-Date).AddSeconds(15) } else { Get-Date }
    while ((Get-Date) -lt $until) {
        $i = Get-RunInfo $Name
        if ($i -and -not $i.alive -and $Name -ne 'mailpit') {
            Write-Bad "$Name exited during start-up"; Show-LogTail $Name; return $false
        }
        if ((Get-Date) -ge $minAlive -and (Test-Healthy $Name)) { Write-Ok "$Name healthy"; return $true }
        Start-Sleep -Seconds 2
    }
    Write-Bad "$Name not healthy after $Seconds s"; Show-LogTail $Name; return $false
}
function Show-Status {
    $rows = foreach ($n in @('mailpit', 'ai-api', 'worker', 'frontend', 'backend')) {
        $i = Get-RunInfo $n
        $healthy = if ($all.Contains($n)) { Test-Healthy $n } else { $false }
        [pscustomobject]@{
            Service = $n
            Managed = if ($i -and $i.alive) { "pid $($i.pid)" } else { '-' }
            Mode    = if ($i -and $i.alive) { $i.mode } else { '-' }
            Healthy = if ($healthy) { 'yes' } else { 'no' }
            Log     = "logs\$n.log"
        }
    }
    $rows | Format-Table -AutoSize | Out-String | Write-Host
    $t = Join-Path $runDir 'tunnel_url.txt'
    $ti = Get-RunInfo 'tunnel'
    if ($ti -and $ti.alive -and (Test-Path -LiteralPath $t)) { Write-Host "Tunnel: $(Get-Content -Raw -LiteralPath $t)" -ForegroundColor Green }
}

# ---------- -SelfTest / -Status / -Stop ----------
if ($SelfTest) {
    $all['selftest'] = @{ Command = "Write-Output 'selftest window'; Start-Sleep -Seconds 900"; Args = @(); Health = 'alive' }
    $i = Get-RunInfo 'selftest'
    if ($i -and $i.alive) {
        Write-Ok 'SELFTEST PASS: the window started by the previous command is still alive - the agent may use start-all.ps1'
        Stop-Service2 'selftest' | Out-Null
        exit 0
    }
    if ($i -and -not $i.alive) {
        Save-RunInfo 'selftest' @{ name = 'selftest'; pid = 0; startTicks = '0'; mode = 'selftest' }
        Write-Bad 'SELFTEST FAIL: the window was closed when the previous command ended - the HUMAN must run start-all.ps1 in their own PowerShell window'
        exit 1
    }
    Start-Service2 'selftest'
    Write-Ok 'selftest window started - wait 5 s, then run start-all.ps1 -SelfTest again as a NEW command'
    exit 0
}
if ($Status) { Show-Status; exit 0 }
if ($Stop) {
    $targets = if ($Only) { $Only } else { @('tunnel', 'backend', 'frontend', 'worker', 'ai-api', 'mailpit') }
    $any = $false
    foreach ($n in $targets) { if (Stop-Service2 $n) { $any = $true } }
    if (-not $any) { Write-Ok 'nothing started by start-all.ps1 is running' }
    $mi = Get-RunInfo 'mailpit'
    if ((Test-PortOpen 8025) -and -not ($mi -and $mi.alive)) { Write-Note 'Mailpit still runs (Docker container or started by hand) - that is fine.' }
    exit 0
}

# ---------- start ----------
if (-not (Test-PortOpen $dbPort $dbHost)) {
    throw "PostgreSQL is not reachable on ${dbHost}:$dbPort - start the Windows service 'postgresql-x64-18' (services.msc) and run again."
}
# a running managed service in another mode (dev/e2e/demo) must be restarted, never mixed:
#   without -Only, -Restart switches the whole stack; with -Only the other services must already be in this mode
foreach ($n in @('backend', 'worker', 'ai-api', 'frontend')) {
    $i = Get-RunInfo $n
    if ($i -and $i.alive -and $i.mode -ne $mode) {
        if ($Only) { throw "$n runs in '$($i.mode)' mode but you asked for '$mode' with -Only. Use the same mode (add or drop -E2E/-Demo), or restart the whole stack without -Only." }
        if (-not $Restart) { throw "$n is running in '$($i.mode)' mode. Add -Restart to switch everything to '$mode' (or -Stop first)." }
    }
}
if ($Restart) {
    $stopList = if ($Only) { $names } else { @('tunnel', 'backend', 'frontend', 'worker', 'ai-api') }   # Mailpit is shared, kept
    foreach ($n in $stopList) { Stop-Service2 $n | Out-Null }
}

$tunnelUrl = $null
if ($Tunnel) {
    $cf = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cf) { throw 'cloudflared not found - winget install Cloudflare.cloudflared' }
    $urlFile = Join-Path $runDir 'tunnel_url.txt'
    Set-Content -LiteralPath $urlFile -Value '' -NoNewline
    $all['tunnel'] = @{ Script = 'start-tunnel.ps1'; Args = @(@('-UrlFile', $urlFile) + @(if ($Demo) { '-Demo' })); Health = 'alive' }
    $ti = Get-RunInfo 'tunnel'
    if ($ti -and $ti.alive) { Stop-Service2 'tunnel' | Out-Null }
    Start-Service2 'tunnel'
    $until = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $until -and -not $tunnelUrl) {
        Start-Sleep -Seconds 2
        $u = (Get-Content -Raw -LiteralPath $urlFile -ErrorAction SilentlyContinue)
        if ($u -match '^https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com$') { $tunnelUrl = $u }
    }
    if (-not $tunnelUrl) { Show-LogTail 'tunnel'; throw 'No tunnel URL after 60 s (internet? cloudflared blocked?).' }
    if ($names -notcontains 'backend') { Write-Note 'the backend must be restarted with the new URL: add -Only backend -Restart -Tunnel' }
    elseif (-not $Restart) {
        $bi = Get-RunInfo 'backend'
        if ($bi -and $bi.alive) { Stop-Service2 'backend' | Out-Null }      # it must learn the new URL
    }
}

$failed = @()
foreach ($n in $names) {
    if ($n -eq 'mailpit' -and (Test-Healthy 'mailpit')) { Write-Ok 'mailpit already running'; continue }
    $i = Get-RunInfo $n
    if ($i -and $i.alive) {
        if (Test-Healthy $n) { Write-Ok "$n already running ($($i.mode))"; continue }
        Write-Note "$n is running but not healthy yet"
        if (-not (Wait-Healthy $n 60)) { $failed += $n }
        continue
    }
    $port = Get-ServicePort $n
    if ($port -and (Test-PortOpen $port) -and $n -ne 'mailpit') {
        Write-Bad "port $port is used by a program start-all.ps1 did not start (an old window? close it, or Task Manager)"
        $failed += $n; continue
    }
    $extra = @(if ($n -eq 'backend' -and $tunnelUrl) { '-BaseUrl', $tunnelUrl })
    Start-Service2 $n $extra
    $limit = if ($n -eq 'backend') { $TimeoutSec } else { [Math]::Min(120, $TimeoutSec) }
    if (-not (Wait-Healthy $n $limit)) { $failed += $n }
}

Show-Status
if ($tunnelUrl) {
    Write-Host "PHONE URL: $tunnelUrl" -ForegroundColor Green
    Write-Host '  Anyone with this URL can open the site - stop it with start-all.ps1 -Stop -Only tunnel when done.' -ForegroundColor Yellow
}
if ($failed.Count) { Write-Bad "not healthy: $($failed -join ', ') - read logs\<service>.log"; exit 1 }
$where = if ($Demo) { 'http://localhost:8080' } else { 'http://localhost:5173' }
Write-Ok "stack '$mode' is up: $where   (Mailpit http://localhost:8025)"
exit 0
