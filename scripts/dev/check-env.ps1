# =============================================================================
# CivicBrain | scripts/dev/check-env.ps1
# Checks one laptop against docs/10_SETUP_WINDOWS.md and prints PASS / WARN / FAIL per item.
#   pwsh -NoProfile -File scripts\dev\check-env.ps1
# Exit code 0 = no FAIL (WARN items are optional tools or things to do later).
# Read-only: installs nothing, changes nothing, never prints secret values.
# =============================================================================
[CmdletBinding()]
param([switch]$SkipDatabase)

. "$PSScriptRoot\_common.ps1"
$script:Fails = 0
$script:Warns = 0
function Pass([string]$m) { Write-Ok $m }
function Fail([string]$m) { Write-Bad $m; $script:Fails++ }
function Warn([string]$m) { Write-Note $m; $script:Warns++ }

# Runs "<exe> <args>" and returns the first output line matching $Pattern (or $null).
function Get-ToolLine([string]$Exe, [string[]]$Arguments, [string]$Pattern = '.') {
    $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = & $cmd.Source @Arguments 2>&1 | ForEach-Object { "$_" } } catch { $out = @() }
    finally { $ErrorActionPreference = $old }
    return ($out | Where-Object { $_ -match $Pattern } | Select-Object -First 1)
}
function Test-Version([string]$Text, [string]$Regex, [scriptblock]$Ok) {
    if (-not $Text -or $Text -notmatch $Regex) { return $false }
    return (& $Ok $Matches)
}

Write-Host "CivicBrain environment check - $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

# ---------- 1. Shell and location ----------
Write-Step 'Shell and repo location'
if ($PSVersionTable.PSVersion -ge [version]'7.4') { Pass "PowerShell $($PSVersionTable.PSVersion)" }
else { Fail "PowerShell $($PSVersionTable.PSVersion) - install PowerShell 7.4+ (winget install Microsoft.PowerShell)" }
if (-not $IsWindows) { Warn 'Not Windows: this kit targets Windows 11 (checks below may differ)' }

$oneDriveRoots = @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer) | Where-Object { $_ }
$inOneDrive = ($RepoRoot -match '(?i)\\OneDrive') -or ($oneDriveRoots | Where-Object { $RepoRoot.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) })
if ($inOneDrive) { Fail "Repo is inside OneDrive ($RepoRoot). Move it to C:\dev\civicbrain (OneDrive breaks node_modules/.venv/target)." }
else { Pass 'Repo is not inside OneDrive' }
if ($RepoRoot -match '^[A-Za-z]:\\?$') { Fail 'Repo is at a drive root - use C:\dev\civicbrain' }
if ($IsWindows -and $RepoRoot -ne 'C:\dev\civicbrain') { Warn "Repo path is $RepoRoot (recommended C:\dev\civicbrain; the agent allow/deny rules assume it)" }
if ($RepoRoot.Length -gt 40) { Warn "Repo path is long ($($RepoRoot.Length) chars) - Windows 260-char limits hit node_modules/.venv sooner" }
if ($IsWindows) {
    try {
        $lp = Get-ItemPropertyValue 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction Stop
        if ($lp -eq 1) { Pass 'Windows long paths enabled' } else { Warn 'Windows long paths disabled (optional: enable LongPathsEnabled; also run: git config --global core.longpaths true)' }
    } catch { Warn 'Could not read LongPathsEnabled' }
}
$blocked = @(Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'scripts') -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $IsWindows -and (Get-Item -LiteralPath $_.FullName -Stream 'Zone.Identifier' -ErrorAction SilentlyContinue) })
if ($blocked.Count -gt 0) { Warn "$($blocked.Count) script(s) still carry the 'downloaded from internet' mark. Run once: Get-ChildItem -Recurse $RepoRoot | Unblock-File" }

# ---------- 2. Core tools ----------
Write-Step 'Core tools'
$git = Get-ToolLine 'git' @('--version') 'git version'
if (Test-Version $git 'git version (\d+)\.(\d+)' { param($m) ([int]$m[1] -gt 2) -or ([int]$m[1] -eq 2 -and [int]$m[2] -ge 45) }) { Pass $git }
elseif ($git) { Warn "$git (2.56.x recommended)" } else { Fail 'git not found (Git for Windows 2.56.x)' }
if ($git) {
    $crlf = Get-ToolLine 'git' @('config', '--global', 'core.autocrlf')
    if ($IsWindows -and $crlf -ne 'true') { Warn "git core.autocrlf is '$crlf' (docs: git config --global core.autocrlf true)" }
}

$java = Get-ToolLine 'java' @('-version') 'version'
if (Test-Version $java 'version "(\d+)' { param($m) [int]$m[1] -eq 25 }) { Pass "Java: $java" }
elseif ($java) { Fail "Java: $java - need Temurin JDK 25 LTS (Spring Boot 4.1 supports 17-26; do not use 27)" }
else { Fail 'java not found - install Eclipse Temurin JDK 25 (tick "Set JAVA_HOME")' }
if (-not $env:JAVA_HOME) { Fail 'JAVA_HOME is not set (mvnw needs it)' }
elseif (-not (Test-Path (Join-Path $env:JAVA_HOME 'bin'))) { Fail "JAVA_HOME points to a missing folder: $env:JAVA_HOME" }
elseif ($env:JAVA_HOME -notmatch '25') { Warn "JAVA_HOME=$env:JAVA_HOME does not look like JDK 25" }
else { Pass "JAVA_HOME=$env:JAVA_HOME" }

$node = Get-ToolLine 'node' @('--version') '^v\d'
if (Test-Version $node '^v(\d+)\.' { param($m) [int]$m[1] -eq 24 }) { Pass "Node.js $node" }
elseif ($node) { Fail "Node.js $node - need Node 24 LTS" } else { Fail 'node not found - install Node.js 24 LTS' }
$npm = Get-ToolLine 'npm' @('--version') '^\d'
if ($npm) { Pass "npm $npm" } else { Fail 'npm not found' }

if ($IsWindows) { $py = Get-ToolLine 'py' @('-3.13', '--version') 'Python' } else { $py = Get-ToolLine 'python3.13' @('--version') 'Python' }
if (Test-Version $py 'Python 3\.13\.' { $true }) { Pass $py } else { Fail 'Python 3.13 not found (py install 3.13). Not 3.14/3.15: no PyTorch wheels guaranteed' }
$venvPy = Join-Path $RepoRoot 'ai-service\.venv\Scripts\python.exe'
if (Test-Path $venvPy) {
    $vv = Get-ToolLine $venvPy @('--version') 'Python'
    if ($vv -match 'Python 3\.13\.') { Pass "ai-service venv: $vv" } else { Fail "ai-service venv uses $vv - recreate it with py -3.13 -m venv .venv" }
} else { Warn 'ai-service\.venv not created yet (docs/10 sec. 3)' }

$uv = Get-ToolLine 'uv' @('--version') 'uv'
if (-not $uv -and (Test-Path $venvPy)) { $uv = Get-ToolLine $venvPy @('-m', 'uv', '--version') 'uv' }
if ($uv) { Pass $uv } else { Warn 'uv not found (needed only to change Python dependencies: py -3.13 -m pip install uv)' }

# ---------- 3. PostgreSQL ----------
Write-Step 'PostgreSQL 18 + PostGIS 3.6'
$envVars = Import-DotEnv -Optional
try {
    $psql = Get-PgTool 'psql'
    $pv = Get-ToolLine $psql @('--version') 'psql'
    if ($pv -match 'PostgreSQL\)?\s+(\d+)' -and [int]$Matches[1] -eq 18) { Pass $pv } else { Fail "$pv - need PostgreSQL 18 client tools" }
    $pgdump = Get-PgTool 'pg_dump'
    Pass "pg_dump found: $pgdump"
} catch { Fail $_.Exception.Message }
if ($IsWindows) {
    $svcs = @(Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue)
    $svc = (@($svcs | Where-Object Name -match '-18$') + @($svcs | Where-Object Status -eq 'Running') + $svcs) | Select-Object -First 1
    if ($svc -and $svc.Status -eq 'Running') { Pass "Service $($svc.Name) running" }
    elseif ($svc) { Fail "Service $($svc.Name) is $($svc.Status)" } else { Fail 'No postgresql Windows service found' }
}
if (-not $SkipDatabase -and $envVars.Count -gt 0 -and $env:PG_ADMIN_PASSWORD -and $env:PG_ADMIN_PASSWORD -notmatch 'change-me') {
    try {
        $row = Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT current_setting('server_version_num') || '|' || coalesce((SELECT default_version FROM pg_available_extensions WHERE name = 'postgis'), 'none')"
        $parts = ($row | Select-Object -Last 1).Split('|')
        if ([int]$parts[0] -ge 180000 -and [int]$parts[0] -lt 190000) { Pass "Server version $($parts[0])" } else { Fail "Server version $($parts[0]) - need PostgreSQL 18" }
        if ($parts[1] -match '^3\.6') { Pass "PostGIS available: $($parts[1])" } else { Fail "PostGIS available: $($parts[1]) - install PostGIS 3.6 bundle via StackBuilder" }
        foreach ($db in @($env:DB_NAME, $env:DB_TEST_NAME, $env:DB_E2E_NAME) | Where-Object { $_ }) {
            $exists = Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_database WHERE datname = '$db'"
            if (($exists | Select-Object -Last 1) -eq '1') { Pass "Database $db exists" } else { Warn "Database $db not created yet (P1)" }
        }
        $roles = Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_roles WHERE rolname IN ('civicbrain_app','civicbrain_ai')"
        if (($roles | Select-Object -Last 1) -eq '2') { Pass 'Roles civicbrain_app and civicbrain_ai exist' } else { Warn 'Login roles not created yet (P1: db-rebuild-test.ps1 or create_roles_template.sql)' }
    } catch { Fail "Cannot connect as PG_ADMIN_USER: $($_.Exception.Message)" }
} else { Warn 'Database connection not checked (.env missing or PG_ADMIN_PASSWORD not set yet)' }

# ---------- 4. Docker / OSRM / Mailpit / tunnel ----------
Write-Step 'Docker, OSRM, Mailpit, cloudflared'
$docker = Get-ToolLine 'docker' @('--version') 'Docker version'
if ($docker) {
    Pass $docker
    $server = Get-ToolLine 'docker' @('info', '--format', '{{.ServerVersion}}') '^\d'
    if ($server) { Pass "Docker engine running ($server)" } else { Warn 'Docker Desktop is installed but not running (needed for OSRM and Testcontainers)' }
    $compose = Get-ToolLine 'docker' @('compose', 'version') 'version'
    if ($compose) { Pass $compose } else { Fail 'docker compose plugin missing' }
} else { Fail 'Docker Desktop not found (needed for OSRM and Testcontainers ITs)' }
if (Test-Path (Join-Path $RepoRoot 'infra\osrm\data\talegaon.osrm.mldgr')) { Pass 'OSRM data prepared (infra/osrm/data)' }
else { Warn 'OSRM data not prepared yet (infra/osrm/README.md, P8)' }
$mail = Get-ToolLine 'mailpit' @('version') 'mailpit'
if (-not $mail) { $mp = Join-Path $RepoRoot 'tools\mailpit\mailpit.exe'; if (Test-Path $mp) { $mail = Get-ToolLine $mp @('version') 'mailpit' } }
if ($mail) { Pass $mail } else { Warn 'mailpit not found on PATH or tools\mailpit\ (start-mailpit.ps1 falls back to Docker)' }
$cf = Get-ToolLine 'cloudflared' @('--version') 'cloudflared'
if ($cf) { Pass $cf } else { Warn 'cloudflared not found (needed to test on phones: winget install Cloudflare.cloudflared)' }

# ---------- 5. Optional tools ----------
Write-Step 'Optional tools'
foreach ($t in @(
        @{ n = 'ffmpeg'; a = @('-version'); p = 'ffmpeg version'; why = 'creates tests/fixtures/images/camera.y4m' },
        @{ n = 'k6'; a = @('version'); p = 'k6'; why = 'P10 load smoke' },
        @{ n = '7z'; a = @(); p = '7-Zip'; why = 'datasets' })) {
    $l = Get-ToolLine $t.n $t.a $t.p
    if ($l) { Pass $l } else { Warn "$($t.n) not found ($($t.why))" }
}
if ($IsWindows) {
    if (Test-Path "$env:ProgramFiles\QGIS*") { Pass 'QGIS installed' } else { Warn 'QGIS not found (P1 ward review)' }
}

# ---------- 6. .env ----------
Write-Step '.env configuration'
$exampleVars = Import-DotEnv -Path (Join-Path $RepoRoot '.env.example') -NoProcessEnv
if ($envVars.Count -eq 0) { Fail '.env missing - Copy-Item .env.example .env and fill it in' }
else {
    $missing = @($exampleVars.Keys | Where-Object { -not $envVars.Contains($_) })
    if ($missing.Count) { Fail ".env lacks keys: $($missing -join ', ')" } else { Pass '.env has every key of .env.example' }
    $placeholders = @($envVars.Keys | Where-Object { $envVars[$_] -match 'REPLACE_WITH|change-me' })
    if ($placeholders.Count) { Fail ".env still has placeholder values for: $($placeholders -join ', ')" } else { Pass 'No placeholder values left' }
    foreach ($k in 'JWT_SECRET', 'OTP_HMAC_KEY', 'TOTP_ENC_KEY', 'AI_SERVICE_JWT_SECRET') {
        $v = [string]$envVars[$k]
        try { $len = [Convert]::FromBase64String($v).Length } catch { $len = -1 }
        if ($k -eq 'TOTP_ENC_KEY' -and $len -ne 32) { Fail "$k must be exactly 32 bytes base64 (found $len)" }
        elseif ($len -lt 32) { Fail "$k must be >= 32 random bytes base64 (found $len) - use scripts\dev\new-secret.ps1" }
        else { Pass "$k length OK ($len bytes)" }
    }
    $distinct = @('JWT_SECRET', 'OTP_HMAC_KEY', 'TOTP_ENC_KEY', 'AI_SERVICE_JWT_SECRET' | ForEach-Object { $envVars[$_] } | Sort-Object -Unique)
    if ($distinct.Count -lt 4) { Fail 'Use a DIFFERENT random value for each secret key' }
    if ($envVars['WHATSAPP_PROVIDER'] -ne 'log') { Warn "WHATSAPP_PROVIDER=$($envVars['WHATSAPP_PROVIDER']) - keep 'log' while the agent is building (docs/10 sec. 5)" }
    foreach ($k in 'STORAGE_ROOT', 'YOLO_WEIGHTS', 'MODELS_DIR') {
        if ($envVars[$k] -and -not [IO.Path]::IsPathRooted($envVars[$k])) { Fail "$k must be an absolute path" }
    }
    if ($envVars['STORAGE_ROOT'] -and -not (Test-Path $envVars['STORAGE_ROOT'])) { Warn "STORAGE_ROOT folder does not exist yet: $($envVars['STORAGE_ROOT'])" }
    if ($envVars['YOLO_WEIGHTS'] -and -not (Test-Path $envVars['YOLO_WEIGHTS'])) { Warn 'YOLO weights not present yet (P2)' }
}
if (Test-Path (Join-Path $RepoRoot '.env.test')) { Pass '.env.test present' } else { Warn '.env.test missing (needed from P4 for E2E: Copy-Item .env.test.example .env.test)' }
$gi = Join-Path $RepoRoot '.gitignore'
if ((Test-Path $gi) -and (Select-String -LiteralPath $gi -Pattern '^\.env$' -Quiet)) { Pass '.gitignore protects .env' } else { Fail '.gitignore missing or does not ignore .env' }

# ---------- 7. Machine ----------
Write-Step 'Machine'
if ($IsWindows) {
    $ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / (1024 * 1024 * 1024), 1)
    if ($ramGb -ge 15) { Pass "RAM $ramGb GB" } elseif ($ramGb -ge 7.5) { Warn "RAM $ramGb GB (8 GB works; OSRM preprocessing and training need more)" } else { Fail "RAM $ramGb GB" }
    $drive = Get-PSDrive -Name $RepoRoot.Substring(0, 1)
    $freeGb = [math]::Round($drive.Free / (1024 * 1024 * 1024), 1)
    if ($freeGb -ge 30) { Pass "Free disk $freeGb GB" } elseif ($freeGb -ge 15) { Warn "Free disk $freeGb GB (30 GB recommended)" } else { Fail "Free disk $freeGb GB" }
}
foreach ($p in @(@{ n = 5432; s = 'PostgreSQL' }, @{ n = 8080; s = 'backend' }, @{ n = 5173; s = 'frontend' }, @{ n = 8001; s = 'AI API' }, @{ n = 5000; s = 'OSRM' }, @{ n = 1025; s = 'Mailpit SMTP' }, @{ n = 8025; s = 'Mailpit UI' })) {
    $state = if (Test-PortOpen $p.n) { 'in use' } else { 'free' }
    Write-Host ("INFO  port {0,-5} {1,-13} {2}" -f $p.n, $p.s, $state)
}

Write-Host ''
if ($script:Fails -gt 0) { Write-Host "RESULT: $script:Fails FAIL, $script:Warns WARN" -ForegroundColor Red; exit 1 }
Write-Host "RESULT: all required checks PASS ($script:Warns WARN)" -ForegroundColor Green
exit 0
