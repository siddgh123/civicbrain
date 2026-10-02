# =============================================================================
# CivicBrain | scripts/dev/prepare-osrm.ps1 - builds the OSRM routing files (MLD) for Talegaon
#   pwsh -NoProfile -File scripts\dev\prepare-osrm.ps1 -Pbf C:\Users\<you>\Downloads\talegaon.osm.pbf
# Uses the image pinned in infra/osrm/docker-compose.yml. Details: infra/osrm/README.md.
# =============================================================================
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Pbf)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7

if (-not (Test-Path -LiteralPath $Pbf)) { throw "PBF file not found: $Pbf" }
if ((Get-Item -LiteralPath $Pbf).Extension -ne '.pbf') { throw 'Expected an .osm.pbf file' }
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) { throw 'docker not found - install Docker Desktop' }
$oldEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
& docker info --format '{{.ServerVersion}}' *> $null
$running = ($LASTEXITCODE -eq 0); $ErrorActionPreference = $oldEap
if (-not $running) { throw 'Docker Desktop is not running - start it and wait until it says "Engine running".' }

$dataDir = Join-Path $RepoRoot 'infra\osrm\data'
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$target = Join-Path $dataDir 'talegaon.osm.pbf'
if ((Resolve-Path -LiteralPath $Pbf).Path -ine $target) {
    Write-Step "Copying $Pbf -> $target"
    Copy-Item -LiteralPath $Pbf -Destination $target -Force
}
$sizeMb = [math]::Round((Get-Item -LiteralPath $target).Length / (1024 * 1024), 1)
Write-Step "Input: talegaon.osm.pbf ($sizeMb MB)"

$compose = @('compose', '-f', $OsrmCompose)
Write-Step 'Pulling the pinned image'
Invoke-Native -Exe 'docker' -Arguments ($compose + @('pull', 'osrm')) -What 'docker compose pull'
Write-Step '1/3 osrm-extract (car profile)'
Invoke-Native -Exe 'docker' -Arguments ($compose + @('run', '--rm', '--no-deps', 'osrm', 'osrm-extract', '-p', '/opt/car.lua', '/data/talegaon.osm.pbf')) -What 'osrm-extract'
Write-Step '2/3 osrm-partition'
Invoke-Native -Exe 'docker' -Arguments ($compose + @('run', '--rm', '--no-deps', 'osrm', 'osrm-partition', '/data/talegaon.osrm')) -What 'osrm-partition'
Write-Step '3/3 osrm-customize'
Invoke-Native -Exe 'docker' -Arguments ($compose + @('run', '--rm', '--no-deps', 'osrm', 'osrm-customize', '/data/talegaon.osrm')) -What 'osrm-customize'

if (Test-Path (Join-Path $dataDir 'talegaon.osrm.mldgr')) {
    Write-Ok 'OSRM data ready (talegaon.osrm.mldgr). Next: scripts\dev\start-osrm.ps1'
} else { throw 'talegaon.osrm.mldgr was not created - read the output above.' }
