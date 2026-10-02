# =============================================================================
# CivicBrain | scripts/dev/db-rebuild-test.ps1 - (re)builds the SQL/AI test database and runs the DB tests
#   pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1            # asks before dropping
#   pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force     # no question (used by verify-all -RebuildTestDb)
# What it does, as PG_ADMIN_USER (same steps as scripts/ci/db-tests.sh in CI):
#   1. creates/updates the login roles civicbrain_app / civicbrain_ai with the passwords from .env
#   2. DROP + CREATE DB_TEST_NAME (only a *_test database; never DB_NAME)
#   3. applies flyway/V*.sql (each in one transaction, exactly like Flyway) and flyway/R__*.sql
#   4. loads db/seed/seed_synthetic_demo_data.sql (unless -NoSeed)
#   5. runs every db/tests/test_*.sql and checks "<NAME> TESTS PASSED: n / n"
# The BACKEND never connects to this database (it has no Flyway history table). The backend and
# Playwright use DB_E2E_NAME (seed-e2e.ps1); AI integration tests use this one.
# =============================================================================
[CmdletBinding()]
param([switch]$Force, [switch]$NoSeed, [switch]$SkipTests)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
Assert-EnvKeys @('DB_TEST_NAME', 'DB_PASSWORD', 'DB_AI_PASSWORD', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD')
$db = $env:DB_TEST_NAME
Assert-DisposableDatabase $db

function ConvertTo-SqlLiteral([string]$s) { "'" + $s.Replace("'", "''") + "'" }

Write-Step 'Login roles (idempotent) + passwords from .env'
$tpl = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'db\tools\create_roles_template.sql')
$rolesSql = $tpl.Replace("'CHANGE_ME_APP_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_PASSWORD)).Replace("'CHANGE_ME_AI_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_AI_PASSWORD))
$rolesSql += "`nALTER ROLE civicbrain_app PASSWORD $(ConvertTo-SqlLiteral $env:DB_PASSWORD);`nALTER ROLE civicbrain_ai PASSWORD $(ConvertTo-SqlLiteral $env:DB_AI_PASSWORD);`n"
Invoke-Psql -Database 'postgres' -StdinSql $rolesSql | Out-Null
Write-Ok 'roles ready'

$exists = (Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_database WHERE datname = '$db'" | Select-Object -Last 1) -eq '1'
if ($exists -and -not $Force) {
    $answer = Read-Host "Database '$db' exists. DROP and rebuild it? (y/N)"
    if ($answer -notin @('y', 'Y', 'yes')) { Write-Host 'Cancelled.'; exit 1 }
}
Write-Step "Re-creating $db"
Invoke-Psql -Database 'postgres' -Command "DROP DATABASE IF EXISTS $db WITH (FORCE)" | Out-Null
Invoke-Psql -Database 'postgres' -Command "CREATE DATABASE $db" | Out-Null

Write-Step 'Migrations (flyway/)'
$versioned = Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'flyway') -Filter 'V*__*.sql' |
    Sort-Object { [int]($_.Name -replace '^V(\d+)__.*$', '$1') }
if (-not $versioned) { throw 'No flyway/V*.sql files found' }
foreach ($f in $versioned) {
    Invoke-Psql -Database $db -File $f.FullName -SingleTransaction | Out-Null
    Write-Ok $f.Name
}
foreach ($f in Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'flyway') -Filter 'R__*.sql') {
    Invoke-Psql -Database $db -File $f.FullName -SingleTransaction | Out-Null
    Write-Ok $f.Name
}

if (-not $NoSeed) {
    Write-Step 'Demo seed'
    Invoke-Psql -Database $db -File (Join-Path $RepoRoot 'db\seed\seed_synthetic_demo_data.sql') | Out-Null
    Write-Ok 'seed_synthetic_demo_data.sql'
}

$facts = Invoke-Psql -Database $db -TuplesOnly -Command "SELECT (SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'spatial_ref_sys') || '|' || (SELECT count(*) FROM wards) || '|' || (SELECT w.ward_number || '/' || w.ward_id FROM fn_locate_point(18.7440, 73.6760) p JOIN wards w ON w.ward_id = p.ward_id)"
$p = ($facts | Select-Object -Last 1).Split('|')
Write-Host "INFO  application tables: $($p[0]) | wards: $($p[1]) | fn_locate_point(18.7440,73.6760) ward_number/ward_id: $($p[2])"
if ([int]$p[0] -lt 74 -or $p[1] -ne '23' -or $p[2] -ne '1/21') { throw 'Schema facts differ from docs/03_DATABASE.md (74 tables, 23 wards, 1/21)' }

if ($SkipTests) { exit 0 }
Write-Step 'SQL tests'
$ok = $true
foreach ($t in Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'db\tests') -Filter 'test_*.sql' | Sort-Object Name) {
    try { $out = Invoke-Psql -Database $db -File $t.FullName } catch { Write-Bad "$($t.Name): $($_.Exception.Message)"; $ok = $false; continue }
    if (-not (Test-SqlTestOutput -Output $out -Name $t.Name)) { $ok = $false }
}
if (-not $ok) { Write-Host 'DB TESTS: FAILED' -ForegroundColor Red; exit 1 }
Write-Host 'DB TESTS: ALL PASSED' -ForegroundColor Green
exit 0
