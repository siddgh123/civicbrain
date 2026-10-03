# =============================================================================
# CivicBrain | scripts/dev/seed-e2e.ps1 - prepares DB_E2E_NAME (civicbrain_e2e) for Playwright
#   pwsh -NoProfile -File scripts\dev\seed-e2e.ps1
#   pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -NoPackage   # E2E stack already running (used by verify-all):
#                                                             reuse the existing jar, do not rebuild
#   pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3   # before P14 the seed runner can only create
#                                                             admin + 2 citizens (officers/contractors come in P14)
# Allowed for the agent (01-safety): it only touches the *_e2e database. Stop the dev stack first:
#   scripts\dev\start-all.ps1 -Stop
# Idempotent. Steps (as PG_ADMIN_USER):
#   1. login roles exist (create_roles_template.sql, passwords from .env)
#   2. create DB_E2E_NAME if missing (empty - Flyway builds it in step 4, so it gets a history table)
#   3. if it is already migrated: db/tools/e2e_reset.sql (empties app tables, keeps reference data)
#   4. runs the backend once with profile `e2e-seed`: Flyway migrates V1..Vn + R__ grants, then
#      E2eSeedRunner creates the fixed accounts from .env.test through the real services
#      (Argon2id hashes, encrypted TOTP secrets, verified e-mails, no forced password change)
#      and the application exits. E2eSeedRunner refuses to run unless the database name ends with _e2e.
# Needs: backend built with E2eSeedRunner (P4), .env and .env.test filled in.
# =============================================================================
[CmdletBinding()]
param([switch]$NoPackage, [ValidateRange(0, 8)][int]$MinAccounts = 8)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
$testVars = Import-DotEnv -Path (Join-Path $RepoRoot '.env.test')
$placeholders = @($testVars.Keys | Where-Object { $testVars[$_] -match '^REPLACE_ME' })
if ($placeholders.Count) { throw ".env.test still has placeholders: $($placeholders -join ', ') (scripts\dev\new-secret.ps1)" }
Assert-EnvKeys @('DB_E2E_NAME', 'DB_PASSWORD', 'DB_AI_PASSWORD', 'DB_HOST', 'DB_PORT')
$db = $env:DB_E2E_NAME
Assert-DisposableDatabase $db
if ($db -notmatch '_e2e$') { throw 'DB_E2E_NAME must end with _e2e' }
if (-not $NoPackage -and (Test-PortOpen 8080)) { throw 'Port 8080 is in use - stop the dev backend first (this script may rebuild backend\target, which a running mvnw process also uses). If the E2E stack is running, use -NoPackage.' }

function ConvertTo-SqlLiteral([string]$s) { "'" + $s.Replace("'", "''") + "'" }
Write-Step 'Login roles'
$tpl = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'db\tools\create_roles_template.sql')
$sql = $tpl.Replace("'CHANGE_ME_APP_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_PASSWORD)).Replace("'CHANGE_ME_AI_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_AI_PASSWORD))
Invoke-Psql -Database 'postgres' -StdinSql $sql | Out-Null

$exists = (Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_database WHERE datname = '$db'" | Select-Object -Last 1) -eq '1'
if (-not $exists) {
    Write-Step "Creating empty database $db (Flyway will migrate it)"
    Invoke-Psql -Database 'postgres' -Command "CREATE DATABASE $db" | Out-Null
} else {
    $migrated = (Invoke-Psql -Database $db -TuplesOnly -Command "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'flyway_schema_history'" | Select-Object -Last 1) -eq '1'
    if ($migrated) {
        Write-Step "Resetting application data in $db"
        $out = Invoke-Psql -Database $db -File (Join-Path $RepoRoot 'db\tools\e2e_reset.sql')
        $out | Where-Object { $_ -match 'E2E RESET DONE' } | ForEach-Object { Write-Ok ($_ -replace '^.*NOTICE:\s+', '') }
    } else {
        $tables = [int](Invoke-Psql -Database $db -TuplesOnly -Command "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'" | Select-Object -Last 1)
        if ($tables -gt 1) { throw "$db has tables but no flyway_schema_history (built by hand?). Drop it in pgAdmin and run this script again." }
    }
}

# UI accounts for the agent's browser checks (E2E database only, never used on dev/demo). The passwords are random
# and live in tests\e2e-ui-accounts.local.json (git-ignored); the agent may read that file, never .env/.env.test.
$uiFile = Join-Path $RepoRoot 'tests\e2e-ui-accounts.local.json'
if (-not (Test-Path -LiteralPath $uiFile)) {
    $rngUi = [System.Security.Cryptography.RandomNumberGenerator]
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $newPw = { 'Ui-' + (-join (1..18 | ForEach-Object { $chars[$rngUi::GetInt32($chars.Length)] })) }
    $ui = [ordered]@{
        note       = 'E2E database only (civicbrain_e2e). Created by seed-e2e.ps1. Safe for the agent to read. Never reuse.'
        admin      = [ordered]@{ email = 'ui.admin@test.local'; password = (& $newPw) }
        officer    = [ordered]@{ email = 'ui.officer@test.local'; password = (& $newPw); scope = 'ROAD, all wards' }
        contractor = [ordered]@{ email = 'ui.contractor@test.local'; password = (& $newPw); firm = 'UI Test Road Works (ROAD)' }
        citizen    = [ordered]@{ email = 'ui.citizen@test.local'; password = (& $newPw) }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $uiFile) | Out-Null
    $ui | ConvertTo-Json | Set-Content -LiteralPath $uiFile -Encoding utf8
    Write-Step 'Created tests\e2e-ui-accounts.local.json (UI accounts for the agent, E2E only)'
}
$uiAcc = Get-Content -Raw -LiteralPath $uiFile | ConvertFrom-Json
foreach ($k in 'admin', 'officer', 'contractor', 'citizen') {
    [Environment]::SetEnvironmentVariable("E2E_UI_$($k.ToUpper())_EMAIL", $uiAcc.$k.email, 'Process')
    [Environment]::SetEnvironmentVariable("E2E_UI_$($k.ToUpper())_PASSWORD", $uiAcc.$k.password, 'Process')
}

Write-Step "Backend (profile e2e-seed) -> migrate + create fixed accounts in $db"
$env:DB_NAME = $db
$env:DB_URL = "jdbc:postgresql://$($env:DB_HOST):$($env:DB_PORT)/$db"
$env:SPRING_PROFILES_ACTIVE = 'e2e-seed'
$env:STORAGE_ROOT = Join-Path $env:STORAGE_ROOT 'e2e'   # same folder as the E2E backend (start-backend.ps1)
$env:SMTP_HOST = 'localhost'; $env:SMTP_PORT = '1025'; $env:SMTP_STARTTLS = 'false'   # never real mail for test accounts
foreach ($k in 'SMTP_USER', 'SMTP_PASSWORD') { [Environment]::SetEnvironmentVariable($k, [NullString]::Value) }   # unset -> no SMTP login; $null would become "" (empty var since .NET 9)
$env:WHATSAPP_PROVIDER = 'log'
$jar = Get-FreshBackendJar -NoPackage:$NoPackage
Invoke-Native -Exe 'java' -Arguments @('-jar', $jar.FullName) -What 'e2e-seed run'

$count = Invoke-Psql -Database $db -TuplesOnly -Command "SELECT count(*) FROM users WHERE email LIKE '%@test.local' AND email NOT LIKE 'ui.%'"
$found = [int]($count | Select-Object -Last 1)
if ($found -lt $MinAccounts) { throw "Expected at least $MinAccounts fixed accounts in $db, found $found" }
if ($found -lt 8) { Write-Note "$found of the 8 fixed accounts exist (officers/contractors are added by the seed runner from P14)" }
Write-Ok "E2E database $db ready with $found fixed accounts (docs/08_TEST_PLAN.md sec. 2)"
