# =============================================================================
# CivicBrain | scripts/dev/backup-db.ps1 - daily pg_dump (custom format) of the main database
#   pwsh -NoProfile -File scripts\dev\backup-db.ps1
#   pwsh -NoProfile -File scripts\dev\backup-db.ps1 -CopyTo E:\civicbrain-backups   # also copy to a USB stick
# Writes backups\<db>_yyyyMMdd_HHmm.backup (git-ignored), checks it with pg_restore --list,
# and removes backups older than -KeepDays (default 14) from backups\ only.
# Restore drill (once per phase, docs/03_DATABASE.md sec. 6): restore into civicbrain_restore_test with
#   pg_restore -h localhost -U postgres -d civicbrain_restore_test --no-owner <file>
# and run db/tests/test_V4.sql there.
# =============================================================================
[CmdletBinding()]
param([string]$Database, [ValidateRange(1, 3650)][int]$KeepDays = 14, [string]$CopyTo)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
if (-not $Database) { $Database = $env:DB_NAME }
Assert-EnvKeys @('DB_HOST', 'DB_PORT', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD')

$dir = Join-Path $RepoRoot 'backups'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$file = Join-Path $dir ("{0}_{1}.backup" -f $Database, (Get-Date -Format 'yyyyMMdd_HHmm'))
$pgDump = Get-PgTool 'pg_dump'
$pgRestore = Get-PgTool 'pg_restore'

$oldPw = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $env:PG_ADMIN_PASSWORD
    Write-Step "pg_dump $Database -> $file"
    & $pgDump -h $env:DB_HOST -p $env:DB_PORT -U $env:PG_ADMIN_USER -d $Database -Fc -Z 6 -f $file
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed (exit $LASTEXITCODE)" }
    $entries = & $pgRestore --list $file
    if ($LASTEXITCODE -ne 0 -or @($entries).Count -lt 50) { throw "Backup check failed: pg_restore --list returned $(@($entries).Count) lines" }
} finally { $env:PGPASSWORD = $oldPw }

$mb = [math]::Round((Get-Item $file).Length / (1024 * 1024), 2)
Write-Ok "Backup OK: $file ($mb MB, $(@($entries).Count) TOC lines)"

if ($CopyTo) {
    New-Item -ItemType Directory -Force -Path $CopyTo | Out-Null
    Copy-Item -LiteralPath $file -Destination $CopyTo
    Write-Ok "Copied to $CopyTo"
}

$old = Get-ChildItem -LiteralPath $dir -Filter '*.backup' | Where-Object { $_.FullName -ne $file -and $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) }
foreach ($f in $old) { Remove-Item -LiteralPath $f.FullName; Write-Host "removed old backup $($f.Name)" }
