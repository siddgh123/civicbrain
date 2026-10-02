# =============================================================================
# CivicBrain | scripts/dev/bootstrap-admin.ps1 - creates the FIRST ADMIN account of a database (FR-04, docs/01 sec. 2)
#   pwsh -NoProfile -File scripts\dev\bootstrap-admin.ps1 -Email admin@tdmc.example
#   pwsh -NoProfile -File scripts\dev\bootstrap-admin.ps1 -Email admin@tdmc.example -Database civicbrain
# Runs the backend once with profile `bootstrap-admin` (non-web): AdminBootstrapRunner creates the ADMIN
# through the normal user service (Argon2id hash, e-mail marked verified; TOTP only if mfa-required=true / P25)
# and exits. It REFUSES if any ADMIN already exists. The password is typed here (hidden), passed to the
# child process in its environment only, and never written to disk or printed.
# Needs: backend built with AdminBootstrapRunner (P3). Stop the dev backend first (the jar may be rebuilt).
# =============================================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')][string]$Email,
    [string]$FullName = 'CivicBrain Administrator',
    [string]$Database
)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null
if ($Database) {
    $env:DB_NAME = $Database
    $env:DB_URL = "jdbc:postgresql://$($env:DB_HOST):$($env:DB_PORT)/$Database"
}
Assert-EnvKeys @('DB_URL', 'DB_USER', 'DB_PASSWORD', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD', 'JWT_SECRET', 'OTP_HMAC_KEY', 'TOTP_ENC_KEY')
if (Test-PortOpen 8080) { throw 'Port 8080 is in use - stop the dev backend first (the jar may be rebuilt).' }

$p1 = Read-Host -AsSecureString 'Password for the new ADMIN (12-128 characters)'
$p2 = Read-Host -AsSecureString 'Repeat the password'
$plain1 = [System.Net.NetworkCredential]::new('', $p1).Password
$plain2 = [System.Net.NetworkCredential]::new('', $p2).Password
if ($plain1 -cne $plain2) { throw 'The two passwords differ.' }
if ($plain1.Length -lt 12 -or $plain1.Length -gt 128) { throw 'Password must be 12-128 characters (docs/07_SECURITY.md sec. 1).' }

$jar = Get-FreshBackendJar
Write-Step "Creating ADMIN $Email in database $env:DB_NAME"
try {
    $env:SPRING_PROFILES_ACTIVE = 'bootstrap-admin'
    $env:BOOTSTRAP_ADMIN_EMAIL = $Email
    $env:BOOTSTRAP_ADMIN_NAME = $FullName
    $env:BOOTSTRAP_ADMIN_PASSWORD = $plain1
    Invoke-Native -Exe 'java' -Arguments @('-jar', $jar.FullName) -What 'bootstrap-admin run'
} finally {
    Remove-Item Env:BOOTSTRAP_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    $plain1 = $null; $plain2 = $null
}
Write-Ok "ADMIN $Email created. First login with e-mail + password (TOTP only if P25 enabled it), then create officers (Admin > Officers)."
