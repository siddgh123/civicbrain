# =============================================================================
# CivicBrain | scripts/dev/start-backend.ps1 - runs the Spring Boot API on http://localhost:8080
#   pwsh -NoProfile -File scripts\dev\start-backend.ps1            # dev: mvnw spring-boot:run
#   pwsh -NoProfile -File scripts\dev\start-backend.ps1 -Prod      # demo: java -jar backend\target\civicbrain-*.jar
#   pwsh -NoProfile -File scripts\dev\start-backend.ps1 -Database civicbrain_e2e -SpringProfile e2e   (used by start-all.ps1 -E2E)
#   ... -BaseUrl https://<name>.trycloudflare.com   (used by start-all.ps1 -Tunnel: links in messages and the
#       Origin check use the tunnel URL; the laptop's own localhost URL stays allowed. .env is not changed.)
# Loads .env into this process only (the values are never printed). Stop with Ctrl+C.
# Needs: PostgreSQL service running, roles created (db-setup-main.ps1), Mailpit for mail in dev.
# Normally started through scripts\dev\start-all.ps1 (own window + logs\backend.log).
# =============================================================================
[CmdletBinding()]
param(
    [switch]$Prod,
    [string]$Database,
    [string]$SpringProfile,
    [string]$BaseUrl
)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7
Import-DotEnv | Out-Null

if ($Database) {
    $env:DB_NAME = $Database
    $env:DB_URL = "jdbc:postgresql://$($env:DB_HOST):$($env:DB_PORT)/$Database"
}
if ($SpringProfile) { $env:SPRING_PROFILES_ACTIVE = $SpringProfile }
if ($env:SPRING_PROFILES_ACTIVE -eq 'e2e') {
    # Playwright opens the SPA on the Vite dev server: links in mails and the Origin check must match it
    $env:APP_BASE_URL = 'http://localhost:5173'
    $env:APP_EXTRA_ORIGINS = 'http://127.0.0.1:5173'
    # Test accounts never get real mail or WhatsApp, whatever .env says (Gmail/Twilio may be set for the demo)
    $env:SMTP_HOST = 'localhost'; $env:SMTP_PORT = '1025'; $env:SMTP_STARTTLS = 'false'
    foreach ($k in 'SMTP_USER', 'SMTP_PASSWORD') { [Environment]::SetEnvironmentVariable($k, $null) }   # unset -> no SMTP login (Mailpit)
    $env:WHATSAPP_PROVIDER = 'log'
}
if ($env:SPRING_PROFILES_ACTIVE -eq 'e2e' -or ($env:DB_E2E_NAME -and $env:DB_NAME -eq $env:DB_E2E_NAME)) {
    # E2E photos live in their own folder, so no cleanup job can ever touch dev/demo photos
    $env:STORAGE_ROOT = Join-Path $env:STORAGE_ROOT 'e2e'
}
if ($Prod -and -not $BaseUrl) {
    # demo jar without tunnel: the laptop browser uses the SPA served on 8080
    $env:APP_BASE_URL = 'http://localhost:8080'
    $env:APP_EXTRA_ORIGINS = 'http://127.0.0.1:8080'
}
if ($BaseUrl) {
    if ($BaseUrl -cnotmatch '^https://[a-z0-9-]+\.trycloudflare\.com$') { throw '-BaseUrl must look like https://<name>.trycloudflare.com' }
    $env:APP_BASE_URL = $BaseUrl
    $env:APP_EXTRA_ORIGINS = if ($Prod) { 'http://localhost:8080' } else { 'http://localhost:5173' }   # laptop browser keeps working
    Write-Step "APP_BASE_URL for this run: $BaseUrl"
}

Assert-EnvKeys @('DB_URL', 'DB_USER', 'DB_PASSWORD', 'PG_ADMIN_USER', 'PG_ADMIN_PASSWORD', 'JWT_SECRET',
    'JWT_ISSUER', 'JWT_AUDIENCE', 'OTP_HMAC_KEY', 'TOTP_ENC_KEY', 'AI_SERVICE_JWT_SECRET', 'STORAGE_ROOT',
    'APP_BASE_URL', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_FROM', 'WHATSAPP_PROVIDER')

if (-not (Test-PortOpen ([int]$env:DB_PORT) $env:DB_HOST)) { throw "PostgreSQL is not reachable on $($env:DB_HOST):$($env:DB_PORT) - start the Windows service." }
# The login roles must exist BEFORE Flyway runs R__civicbrain_grants.sql the first time (otherwise Flyway
# records it as applied without grants and does not re-apply it until the file changes).
$roles = Invoke-Psql -Database 'postgres' -TuplesOnly -Command "SELECT count(*) FROM pg_roles WHERE rolname IN ('civicbrain_app','civicbrain_ai')" | Select-Object -Last 1
if ($roles -ne '2') { throw 'Login roles civicbrain_app / civicbrain_ai do not exist - run scripts\dev\db-setup-main.ps1 first (it creates them from .env).' }
if (Test-PortOpen 8080) { throw 'Port 8080 is already in use - is the backend already running?' }
if (-not (Test-Path $env:STORAGE_ROOT)) { New-Item -ItemType Directory -Path $env:STORAGE_ROOT | Out-Null; Write-Step "Created STORAGE_ROOT $env:STORAGE_ROOT" }
if ($env:SPRING_PROFILES_ACTIVE -eq 'dev' -and $env:SMTP_PORT -eq '1025' -and -not (Test-PortOpen 1025)) {
    Write-Note 'Mailpit is not running (port 1025) - e-mails will fail and retry. Start it with start-mailpit.ps1'
}

$backend = Join-Path $RepoRoot 'backend'
Write-Step "Backend: profile=$env:SPRING_PROFILES_ACTIVE database=$env:DB_NAME"
if ($Prod) {
    $jar = Get-ChildItem (Join-Path $backend 'target') -Filter 'civicbrain-*.jar' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch 'plain|sources|javadoc' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $jar) { throw 'No backend\target\civicbrain-*.jar - build it: cd backend; .\mvnw.cmd -q -DskipTests package' }
    Invoke-Native -Exe 'java' -Arguments @('-jar', $jar.FullName) -WorkingDirectory $RepoRoot -What 'backend'
} else {
    $mvnw = Join-Path $backend 'mvnw.cmd'
    if (-not (Test-Path $mvnw)) { throw 'backend\mvnw.cmd not found - the backend skeleton is created in P0.' }
    Invoke-Native -Exe $mvnw -Arguments @('-q', 'spring-boot:run') -WorkingDirectory $backend -What 'backend'
}
