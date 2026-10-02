# =============================================================================
# CivicBrain | scripts/dev/install-all.ps1 - installs the MVP software with winget (HUMAN runs it once)
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\dev\install-all.ps1
#   (first time on a new laptop you may still be in Windows PowerShell 5.1 - that is fine for this script)
# Installs what is missing, skips what is already there, prints a summary and the manual steps left:
#   PostgreSQL 18 opens its normal installer (you choose the postgres password - remember it), then
#   StackBuilder -> Spatial Extensions -> PostGIS 3.6 bundle; Docker Desktop needs one restart.
# Versions: docs/10_SETUP_WINDOWS.md sec. 2. Safe to run again.
# =============================================================================
[CmdletBinding()]
param([switch]$IncludeOptional)
$ErrorActionPreference = 'Stop'

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget not found. Install "App Installer" from the Microsoft Store, then run this script again.'
}

# id | name | extra winget arguments | optional
$packages = @(
    @{ Id = 'Microsoft.PowerShell';           Name = 'PowerShell 7' },
    @{ Id = 'Git.Git';                        Name = 'Git for Windows' },
    @{ Id = 'EclipseAdoptium.Temurin.25.JDK'; Name = 'Temurin JDK 25 (+ JAVA_HOME)'; Custom = 'ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome' },
    @{ Id = 'OpenJS.NodeJS.LTS';              Name = 'Node.js LTS (must be 24.x)' },
    @{ Id = 'Python.Python.3.13';             Name = 'Python 3.13' },
    @{ Id = 'PostgreSQL.PostgreSQL.18';       Name = 'PostgreSQL 18 (installer window opens)'; Interactive = $true },
    @{ Id = 'PostgreSQL.pgAdmin';             Name = 'pgAdmin 4' },
    @{ Id = 'Docker.DockerDesktop';           Name = 'Docker Desktop' },
    @{ Id = 'Cloudflare.cloudflared';         Name = 'cloudflared' },
    @{ Id = 'Google.Chrome';                  Name = 'Google Chrome' },
    @{ Id = 'Google.AntigravityIDE';          Name = 'Google Antigravity IDE (only if you use it instead of Claude Code)'; Optional = $true },
    @{ Id = 'Gyan.FFmpeg';                    Name = 'ffmpeg (fake camera for tests)'; Optional = $true },
    @{ Id = 'OSGeo.QGIS_LTR';                 Name = 'QGIS LTR (ward review)'; Optional = $true }
)

$results = @()
foreach ($p in $packages) {
    if ($p.Optional -and -not $IncludeOptional) { $results += [pscustomobject]@{ Package = $p.Name; Result = 'skipped (optional, use -IncludeOptional)' }; continue }
    Write-Host "==> $($p.Name) [$($p.Id)]" -ForegroundColor Cyan
    & winget list --id $p.Id --exact --accept-source-agreements *> $null
    if ($LASTEXITCODE -eq 0) { $results += [pscustomobject]@{ Package = $p.Name; Result = 'already installed' }; continue }
    $wingetArgs = @('install', '--id', $p.Id, '--exact', '--accept-package-agreements', '--accept-source-agreements')
    if ($p.Interactive) { $wingetArgs += '--interactive' } else { $wingetArgs += '--silent' }
    if ($p.Custom) { $wingetArgs += @('--custom', $p.Custom) }      # extra installer arguments (Temurin: also set JAVA_HOME)
    & winget @wingetArgs
    $results += [pscustomobject]@{ Package = $p.Name; Result = $(if ($LASTEXITCODE -eq 0) { 'INSTALLED' } else { "FAILED (exit $LASTEXITCODE) - install it by hand, see docs/10_SETUP_WINDOWS.md" }) }
}

# JAVA_HOME: the Temurin MSI sets it only with FeatureJavaHome; if Temurin was already installed without it, set it here
$javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'User')
if (-not $javaHome) { $javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine') }
if (-not $javaHome) {
    $jdk = Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -Filter 'jdk-25*' -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($jdk) {
        [Environment]::SetEnvironmentVariable('JAVA_HOME', $jdk.FullName, 'User')
        $results += [pscustomobject]@{ Package = 'JAVA_HOME'; Result = "set to $($jdk.FullName) (for your user)" }
    } else {
        $results += [pscustomobject]@{ Package = 'JAVA_HOME'; Result = 'NOT SET - JDK 25 folder not found, see START_HERE.md' }
    }
}

Write-Host ''
$results | Format-Table -AutoSize | Out-String | Write-Host
Write-Host @'
MANUAL STEPS LEFT (about 30 minutes):
 (START_HERE.md steps 3.3 - 4 have the details)
 1. If not done yet: PostGIS via Stack Builder -> PostgreSQL 18 -> Spatial Extensions -> PostGIS 3.6 Bundle.
 2. Restart Windows once (Docker Desktop + PATH). Open Docker Desktop once and accept; it installs/updates WSL 2.
 3. Create C:\Users\<you>\.wslconfig with "[wsl2]" and "memory=4GB", then run: wsl --shutdown
 4. Mailpit: nothing to install - start-all.ps1 runs it in Docker.
 5. Open PowerShell 7 (pwsh) in C:\dev\civicbrain: Unblock-File, git config user.name/user.email,
    then: pwsh -NoProfile -File scripts\dev\new-env.ps1
'@ -ForegroundColor Yellow
