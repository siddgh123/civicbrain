# =============================================================================
# CivicBrain | scripts/dev/_common.ps1  - shared helpers, dot-sourced by the other scripts:
#     . "$PSScriptRoot\_common.ps1"
# For HUMANS on Windows 11 + PowerShell 7. The Antigravity agent never runs start-* scripts.
# Never prints secret values.
# =============================================================================
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message)   { Write-Host "PASS  $Message" -ForegroundColor Green }
function Write-Bad([string]$Message)  { Write-Host "FAIL  $Message" -ForegroundColor Red }
function Write-Note([string]$Message) { Write-Host "WARN  $Message" -ForegroundColor Yellow }

function Assert-PowerShell7 {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw "Use PowerShell 7 (pwsh), not Windows PowerShell 5.1. Install: winget install Microsoft.PowerShell"
    }
}

# Reads KEY=VALUE lines into the current process environment (child processes inherit them).
# Supports comments (#), blank lines, "double" or 'single' quoted values, and inline " # comments"
# after unquoted values. Returns an ordered dictionary. Never prints values.
function Import-DotEnv {
    param(
        [string]$Path = (Join-Path $script:RepoRoot '.env'),
        [switch]$Optional,
        [switch]$NoProcessEnv
    )
    $vars = [ordered]@{}
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($Optional) { return $vars }
        throw "Missing $Path. Create it with:  Copy-Item .env.example .env   and fill in local values."
    }
    $lineNo = 0
    foreach ($raw in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $lineNo++
        $line = $raw.Trim()
        if ($line -eq '' -or $line.StartsWith('#')) { continue }
        if ($line.StartsWith('export ')) { $line = $line.Substring(7).Trim() }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { throw "$Path line ${lineNo}: expected KEY=VALUE" }
        $key = $line.Substring(0, $idx).Trim()
        if ($key -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "$Path line ${lineNo}: invalid key '$key'" }
        $val = $line.Substring($idx + 1).Trim()
        if ($val -match '^"(.*?)"(\s+#.*)?$' -or $val -match "^'(.*?)'(\s+#.*)?$") {
            $val = $Matches[1]                                   # quoted value, optional trailing comment
        } else {
            $hash = $val.IndexOf(' #')
            if ($hash -ge 0) { $val = $val.Substring(0, $hash).TrimEnd() }
        }
        $vars[$key] = $val
        if (-not $NoProcessEnv) {
            # KEY= (empty) removes the variable, as before .NET 9: since .NET 9 SetEnvironmentVariable(name, "") keeps an
            # empty variable, which would hide Spring defaults like ${KEY:x}; [NullString]::Value is the real null
            if ($val -eq '') { [Environment]::SetEnvironmentVariable($key, [NullString]::Value, 'Process') }
            else { [Environment]::SetEnvironmentVariable($key, $val, 'Process') }
        }
    }
    return $vars
}

# Throws if any of the keys is missing or empty in the process environment.
function Assert-EnvKeys([string[]]$Keys) {
    $missing = @($Keys | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_)) })
    if ($missing.Count -gt 0) { throw "Missing values in .env: $($missing -join ', ') (see .env.example)" }
}

# Finds a PostgreSQL client tool (psql, pg_dump, pg_restore, createdb) - PG_BIN, then PATH,
# then the newest C:\Program Files\PostgreSQL\<n>\bin.
function Get-PgTool([Parameter(Mandatory)][string]$Name) {
    $exe = if ($IsWindows) { "$Name.exe" } else { $Name }
    if ($env:PG_BIN) {
        $p = Join-Path $env:PG_BIN $exe
        if (Test-Path -LiteralPath $p) { return $p }
    }
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if ($IsWindows) {
        $dirs = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d+$' } | Sort-Object { [int]$_.Name } -Descending
        foreach ($d in $dirs) {
            $p = Join-Path $d.FullName "bin\$exe"
            if (Test-Path -LiteralPath $p) { return $p }
        }
    }
    throw "$Name not found. Set PG_BIN in .env (e.g. C:\Program Files\PostgreSQL\18\bin)."
}

# Runs psql as PG_ADMIN_USER. Returns the output lines (NOTICEs included). Throws on error.
function Invoke-Psql {
    param(
        [Parameter(Mandatory)][string]$Database,
        [string]$File,
        [string]$Command,
        [string]$StdinSql,
        [switch]$SingleTransaction,
        [switch]$TuplesOnly
    )
    Assert-EnvKeys @('DB_HOST', 'DB_PORT', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD')
    $psql = Get-PgTool 'psql'
    $psqlArgs = @('-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', $env:DB_HOST, '-p', $env:DB_PORT,
              '-U', $env:PG_ADMIN_USER, '-d', $Database)
    if ($SingleTransaction) { $psqlArgs += '-1' }
    if ($TuplesOnly) { $psqlArgs += @('-A', '-t') }
    if ($File) { $psqlArgs += @('-f', $File) }
    elseif ($Command) { $psqlArgs += @('-c', $Command) }
    elseif ($StdinSql) { $psqlArgs += @('-f', '-') }
    else { throw 'Invoke-Psql needs -File, -Command or -StdinSql' }

    $oldPw = $env:PGPASSWORD
    $oldEap = $ErrorActionPreference
    try {
        $env:PGPASSWORD = $env:PG_ADMIN_PASSWORD
        $ErrorActionPreference = 'Continue'   # psql writes NOTICEs to stderr
        if ($StdinSql) { $out = $StdinSql | & $psql @psqlArgs 2>&1 | ForEach-Object { "$_" } }
        else { $out = & $psql @psqlArgs 2>&1 | ForEach-Object { "$_" } }
        $code = $LASTEXITCODE
    } finally {
        $env:PGPASSWORD = $oldPw
        $ErrorActionPreference = $oldEap
    }
    if ($code -ne 0) {
        $out | Select-Object -Last 40 | ForEach-Object { Write-Host $_ }
        throw "psql failed (exit $code) on database $Database"
    }
    return @($out)
}

# Checks the output of one db/tests file: needs "<NAME> TESTS PASSED: n / n" and no "NOTICE: FAIL".
function Test-SqlTestOutput([string[]]$Output, [string]$Name) {
    $summary = $Output | Select-String -Pattern '([A-Z0-9 ]+TESTS PASSED: (\d+) / (\d+))' | Select-Object -Last 1
    $fails = @($Output | Select-String -Pattern 'NOTICE:\s+FAIL')
    if (-not $summary) { Write-Bad "$Name (no 'TESTS PASSED' summary)"; return $false }
    $m = $summary.Matches[0]
    if ($fails.Count -gt 0 -or $m.Groups[2].Value -ne $m.Groups[3].Value) {
        $fails | ForEach-Object { Write-Host $_.Line }
        Write-Bad "$Name -> $($m.Groups[1].Value.Trim())"; return $false
    }
    Write-Ok "$Name -> $($m.Groups[1].Value.Trim())"; return $true
}

# Runs a native command, streams its output, throws with a clear message if it fails.
# CB_MERGE_STDERR=1 (set by start-all.ps1 for its service windows): stderr is merged into stdout as plain
# text, so uvicorn/worker/maven messages reach the service log file (logs\<service>.log) too.
function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [string[]]$Arguments = @(), [string]$WorkingDirectory = $script:RepoRoot, [string]$What = $Exe)
    Push-Location $WorkingDirectory
    try {
        if ($env:CB_MERGE_STDERR -eq '1') { & $Exe @Arguments 2>&1 | ForEach-Object { "$_" } }
        else { & $Exe @Arguments }
        if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}

# True if something is listening. 'localhost' checks BOTH loopbacks: Vite (Node >= 17) binds [::1]
# only on Windows, while Mailpit, uvicorn and Docker publish on 127.0.0.1 only.
function Test-PortOpen([int]$Port, [string]$HostName = 'localhost') {
    $targets = if ($HostName -eq 'localhost') { @('127.0.0.1', '::1') } else { @($HostName) }
    foreach ($h in $targets) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try { if ($client.ConnectAsync($h, $Port).Wait(500) -and $client.Connected) { return $true } }
        catch { } finally { $client.Dispose() }
    }
    return $false
}

# Guard: only the two throw-away databases may be dropped/reset by scripts.
function Assert-DisposableDatabase([string]$Name) {
    if ($Name -cnotmatch '^[a-z][a-z0-9_]*_(test|e2e)$') { throw "Refusing: '$Name' is not a lower-case *_test or *_e2e database name." }
    if ($env:DB_NAME -and $Name -eq $env:DB_NAME) { throw "Refusing: '$Name' is the main database (DB_NAME)." }
}

# Returns the backend jar (backend\target\civicbrain-*.jar). Unless -NoPackage, rebuilds it first when it is
# missing or older than any file in backend\src or pom.xml (tests skipped here; verify-all runs them).
# Do not run this while a dev backend (mvnw spring-boot:run) uses backend\target.
function Get-FreshBackendJar([switch]$NoPackage) {
    $backend = Join-Path $script:RepoRoot 'backend'
    $find = {
        Get-ChildItem (Join-Path $backend 'target') -Filter 'civicbrain-*.jar' -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notmatch 'plain|sources|javadoc' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    $jar = & $find
    if ($NoPackage) {
        if (-not $jar) { throw 'No backend\target\civicbrain-*.jar yet - run once without -NoPackage.' }
        return $jar
    }
    $newestSrc = Get-ChildItem (Join-Path $backend 'src'), (Join-Path $backend 'pom.xml') -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $jar -or ($newestSrc -and $newestSrc.LastWriteTime -gt $jar.LastWriteTime)) {
        Write-Step 'Backend jar missing or older than the sources - packaging (tests skipped here)'
        $mvnw = Join-Path $backend 'mvnw.cmd'
        if (-not (Test-Path $mvnw)) { throw 'backend\mvnw.cmd not found (backend skeleton is created in P0).' }
        Invoke-Native -Exe $mvnw -Arguments @('-q', '-DskipTests', 'package') -WorkingDirectory $backend -What 'mvnw package' | Out-Host
        $jar = & $find
        if (-not $jar) { throw 'mvnw package did not produce backend\target\civicbrain-*.jar (artifactId must be civicbrain)' }
    }
    return $jar
}

# The OSRM image is defined once, in infra/osrm/docker-compose.yml; scripts use `docker compose`.
$script:OsrmCompose = Join-Path $script:RepoRoot 'infra\osrm\docker-compose.yml'
