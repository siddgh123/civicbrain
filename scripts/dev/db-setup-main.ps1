# =============================================================================
# CivicBrain | scripts/dev/db-setup-main.ps1 - prepares the MAIN dev database (DB_NAME, normally civicbrain)
#   pwsh -NoProfile -File scripts\dev\db-setup-main.ps1          # 1) login roles + empty database
#   pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed    # 2) after the backend's first start: demo data
# Step 1 (before the backend ever starts): creates/updates the roles civicbrain_app / civicbrain_ai with the
#   .env passwords and creates DB_NAME if it does not exist. Flyway (backend start) then builds V1..V5 + R__.
#   (This replaces restoring civicbrain_backup: V1..V4 from empty gives the same data - docs/00 verified facts.)
# Step 2: loads db/seed/seed_synthetic_demo_data.sql (500 synthetic complaints, Step 12/13 results) - only if
#   Flyway has migrated the database (version 5 present) and the complaints table is still empty.
# NEVER drops or empties anything. Allowed for the Antigravity agent in autopilot mode (.agents/rules/01-safety.md).
# =============================================================================
[CmdletBinding()]
param([switch]$Seed)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
Assert-EnvKeys @('DB_NAME', 'DB_PASSWORD', 'DB_AI_PASSWORD', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD')
$db = $env:DB_NAME
if ($db -cnotmatch '^[a-z][a-z0-9_]*$') { throw "DB_NAME '$db' must be lower-case letters, digits, underscore." }
function ConvertTo-SqlLiteral([string]$s) { "'" + $s.Replace("'", "''") + "'" }

if (-not $Seed) {
    Write-Step 'Login roles (create if missing, passwords from .env)'
    $tpl = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'db\tools\create_roles_template.sql')
    $sql = $tpl.Replace("'CHANGE_ME_APP_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_PASSWORD)).Replace("'CHANGE_ME_AI_PASSWORD'", (ConvertTo-SqlLiteral $env:DB_AI_PASSWORD))
    $sql += "`nALTER ROLE civicbrain_app PASSWORD $(ConvertTo-SqlLiteral $env:DB_PASSWORD);`nALTER ROLE civicbrain_ai PASSWORD $(ConvertTo-SqlLiteral $env:DB_AI_PASSWORD);`n"
    Invoke-Psql -Database 'postgres' -StdinSql $sql | Out-Null
    Write-Ok 'roles civicbrain_app and civicbrain_ai ready'

    $exists = (Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_database WHERE datname = '$db'" | Select-Object -Last 1) -eq '1'
    if ($exists) {
        Write-Ok "database $db already exists (left unchanged)"
    } else {
        Invoke-Psql -Database 'postgres' -Command "CREATE DATABASE $db" | Out-Null
        Write-Ok "database $db created (empty - Flyway builds it when the backend starts)"
    }
    Write-Host 'Next: start the backend once (scripts\dev\start-backend.ps1 or start-all.ps1), then run this script with -Seed.' -ForegroundColor Green
    exit 0
}

Write-Step "Demo seed into $db"
$hasHistory = (Invoke-Psql -Database $db -TuplesOnly -Command "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename='flyway_schema_history'" | Select-Object -Last 1) -eq '1'
if (-not $hasHistory) { throw "Flyway has not migrated $db yet - start the backend once first." }
$v5 = Invoke-Psql -Database $db -TuplesOnly -Command "SELECT count(*) FROM flyway_schema_history WHERE version = '5' AND success" | Select-Object -Last 1
if ($v5 -ne '1') { throw "V5 is not applied in $db (check flyway_schema_history / backend log)." }
$complaints = [int](Invoke-Psql -Database $db -TuplesOnly -Command 'SELECT count(*) FROM complaints' | Select-Object -Last 1)
if ($complaints -gt 0) { Write-Ok "complaints already has $complaints rows - seed skipped (it is meant for an empty database)"; exit 0 }
Invoke-Psql -Database $db -File (Join-Path $RepoRoot 'db\seed\seed_synthetic_demo_data.sql') | Out-Null
$facts = Invoke-Psql -Database $db -TuplesOnly -Command "SELECT (SELECT count(*) FROM complaints) || '|' || (SELECT count(*) FROM wards) || '|' || (SELECT count(*) FROM roads)" | Select-Object -Last 1
$c, $w, $r = $facts.Split('|')
Write-Ok "seed loaded: complaints=$c (synthetic, SUBMITTED, never analysed), wards=$w, roads=$r"
if ([int]$c -ne 500 -or [int]$w -ne 23) { throw 'Unexpected counts (expected 500 complaints, 23 wards).' }
