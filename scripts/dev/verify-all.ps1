# =============================================================================
# CivicBrain | scripts/dev/verify-all.ps1 - the phase-gate proof (docs/08_TEST_PLAN.md sec. 1)
# Runs, in order, stopping at the first failure:  DB -> backend -> AI -> frontend -> E2E
#   pwsh -NoProfile -File scripts\dev\verify-all.ps1                   # everything (E2E needs start-e2e.ps1 running)
#   pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E          # no services needed
#   pwsh -NoProfile -File scripts\dev\verify-all.ps1 -RebuildTestDb    # rebuild civicbrain_test first
# Components that do not exist yet (before P0/P3/P6) are reported as SKIP, not PASS.
# The full log is saved to logs\verify-all_<timestamp>.txt - paste the summary into docs/PROGRESS.md.
# Exit code 0 only if every executed step passed.
# =============================================================================
[CmdletBinding()]
param([switch]$SkipE2E, [switch]$RebuildTestDb, [switch]$SkipDb)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
$dotenv = Import-DotEnv   # needed for the DB step; hidden again from the test runs below (same as CI)

$logDir = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("verify-all_{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
Start-Transcript -LiteralPath $log | Out-Null
$results = [System.Collections.Generic.List[object]]::new()
$failed = $false

function Invoke-Step([string]$Name, [scriptblock]$Body) {
    if ($script:failed) { $script:results.Add([pscustomobject]@{ Step = $Name; Result = 'NOT RUN'; Seconds = 0 }); return }
    Write-Step $Name
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $status = 'PASS'
    try {
        $r = & $Body
        if (@($r) -contains 'SKIP') { $status = 'SKIP' }
    } catch {
        $status = 'FAIL'
        Write-Bad "$Name : $($_.Exception.Message)"
        $script:failed = $true
    }
    $script:results.Add([pscustomobject]@{ Step = $Name; Result = $status; Seconds = [math]::Round($sw.Elapsed.TotalSeconds) })
}
# Runs $Body with some environment variables replaced ($null = removed) and restores them afterwards.
function Invoke-WithEnv([hashtable]$Vars, [scriptblock]$Body) {
    $saved = @{}
    foreach ($k in $Vars.Keys) { $saved[$k] = [Environment]::GetEnvironmentVariable($k); [Environment]::SetEnvironmentVariable($k, $Vars[$k]) }
    try { & $Body } finally { foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) } }
}
function Invoke-Checked([string]$Exe, [string[]]$Arguments, [string]$Dir, [string]$What) {
    Push-Location $Dir
    try { & $Exe @Arguments | Out-Host; if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)" } } finally { Pop-Location }
}

try {
    # ---------- 1. Database ----------
    Invoke-Step 'DB: SQL tests on DB_TEST_NAME' {
        if ($SkipDb) { return 'SKIP' }
        if ($RebuildTestDb) {
            & (Join-Path $PSScriptRoot 'db-rebuild-test.ps1') -Force | Out-Host
            if ($LASTEXITCODE -ne 0) { throw 'db-rebuild-test failed' }
            return
        }
        $db = $env:DB_TEST_NAME
        $exists = (Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_database WHERE datname = '$db'" | Select-Object -Last 1) -eq '1'
        if (-not $exists) { throw "$db does not exist - run scripts\dev\db-rebuild-test.ps1 (or verify-all -RebuildTestDb)" }
        $ok = $true
        foreach ($t in Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'db\tests') -Filter 'test_*.sql' | Sort-Object Name) {
            $out = Invoke-Psql -Database $db -File $t.FullName
            if (-not (Test-SqlTestOutput -Output $out -Name $t.Name)) { $ok = $false }
        }
        if (-not $ok) { throw 'one or more SQL test files failed' }
    }

    # ---------- 2. Backend ----------
    Invoke-Step 'Backend: mvnw verify (unit + Testcontainers IT + coverage)' {
        $be = Join-Path $RepoRoot 'backend'
        if (-not (Test-Path (Join-Path $be 'mvnw.cmd'))) { Write-Note 'backend not created yet'; return 'SKIP' }
        $noDotEnv = @{}; foreach ($k in $dotenv.Keys) { $noDotEnv[$k] = $null }   # CI runs mvnw verify without .env values
        Invoke-WithEnv $noDotEnv { Invoke-Checked (Join-Path $be 'mvnw.cmd') @('-q', '-B', 'verify') $be 'mvnw verify' }
    }

    # ---------- 3. AI service ----------
    Invoke-Step 'AI: ruff + pytest' {
        $ai = Join-Path $RepoRoot 'ai-service'
        $py = Join-Path $ai '.venv\Scripts\python.exe'
        if (-not (Test-Path $py) -or -not (Test-Path (Join-Path $ai 'tests'))) { Write-Note 'ai-service venv/tests not created yet'; return 'SKIP' }
        Invoke-WithEnv @{ DB_NAME = $env:DB_TEST_NAME } {   # same as CI: tests never see the main database name
            Invoke-Checked $py @('-m', 'ruff', 'check', '.') $ai 'ruff'
            Invoke-Checked $py @('-m', 'pytest', '-q') $ai 'pytest'
        }
    }

    # ---------- 4. Frontend ----------
    Invoke-Step 'Frontend: lint + typecheck + vitest' {
        $fe = Join-Path $RepoRoot 'frontend'
        if (-not (Test-Path (Join-Path $fe 'node_modules'))) { Write-Note 'frontend not installed yet (npm install)'; return 'SKIP' }
        $npm = if ($IsWindows) { 'npm.cmd' } else { 'npm' }
        Invoke-Checked $npm @('run', 'lint') $fe 'eslint'
        Invoke-Checked $npm @('run', 'typecheck') $fe 'tsc'
        Invoke-Checked $npm @('test', '--', '--run') $fe 'vitest'
    }

    # ---------- 5. E2E ----------
    Invoke-Step 'E2E: Playwright (desktop + Pixel 7)' {
        if ($SkipE2E) { return 'SKIP' }
        $fe = Join-Path $RepoRoot 'frontend'
        if (-not (Test-Path (Join-Path $fe 'e2e'))) { Write-Note 'frontend/e2e not created yet'; return 'SKIP' }
        foreach ($p in 8080, 8025) { if (-not (Test-PortOpen $p)) { throw "port $p is not listening - run scripts\dev\start-e2e.ps1 first (or use -SkipE2E)" } }
        # the backend on :8080 must be the E2E stack, never the dev/demo backend on the real database
        $appConn = Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT coalesce(sum(CASE WHEN datname = '$($env:DB_E2E_NAME)' THEN 1 ELSE 0 END),0) || '|' || coalesce(sum(CASE WHEN datname = '$($env:DB_NAME)' THEN 1 ELSE 0 END),0) FROM pg_stat_activity WHERE usename = '$($env:DB_USER)'" | Select-Object -Last 1
        $e2eConn, $mainConn = $appConn.Split('|')
        if ([int]$e2eConn -eq 0 -or [int]$mainConn -gt 0) {
            throw "The backend on :8080 is not the E2E stack (API connections: $($env:DB_E2E_NAME)=$e2eConn, $($env:DB_NAME)=$mainConn). Stop the dev/demo services and run start-e2e.ps1."
        }
        # every run starts from the same data (docs/08_TEST_PLAN.md sec. 4)
        & (Join-Path $PSScriptRoot 'seed-e2e.ps1') -NoPackage | Out-Host
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'seed-e2e -NoPackage failed' }
        $npx = if ($IsWindows) { 'npx.cmd' } else { 'npx' }
        Invoke-Checked $npx @('playwright', 'test') $fe 'playwright'
    }
} finally {
    Write-Host ''
    Write-Host 'SUMMARY' -ForegroundColor Cyan
    $results | Format-Table -AutoSize | Out-String | Write-Host
    $verdict = if ($failed) { 'VERIFY-ALL: FAILED' } else { 'VERIFY-ALL: GREEN (SKIP = component not built yet)' }
    Write-Host $verdict -ForegroundColor $(if ($failed) { 'Red' } else { 'Green' })
    Write-Host "log: $log"
    Stop-Transcript | Out-Null
}
if ($failed) { exit 1 }
exit 0
