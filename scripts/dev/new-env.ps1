# =============================================================================
# CivicBrain | scripts/dev/new-env.ps1 - writes .env and .env.test with fresh random secrets (HUMAN runs it once)
#   pwsh -NoProfile -File scripts\dev\new-env.ps1            # asks only for the postgres password
#   pwsh -NoProfile -File scripts\dev\new-env.ps1 -Force     # overwrite existing files (old secrets are lost)
# Fills: JWT_SECRET, OTP_HMAC_KEY, TOTP_ENC_KEY, AI_SERVICE_JWT_SECRET (32 random bytes each, different),
#        DB_PASSWORD / DB_AI_PASSWORD (random role passwords), PG_ADMIN_PASSWORD (you type it, hidden),
#        PG_BIN (detected), every path from this repo's real location; .env.test: random passwords + TOTP secrets.
# Keeps the safe dev defaults (Mailpit, WHATSAPP_PROVIDER=log). Gmail/Twilio values are added later by hand.
# Never prints a secret. The Antigravity agent never runs this script and never opens .env.
# =============================================================================
[CmdletBinding()]
param([switch]$Force)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7

$envFile = Join-Path $RepoRoot '.env'
$envTestFile = Join-Path $RepoRoot '.env.test'
if (((Test-Path $envFile) -or (Test-Path $envTestFile)) -and -not $Force) {
    throw '.env or .env.test already exists. Use -Force to overwrite (all old secrets are replaced).'
}

$rng = [System.Security.Cryptography.RandomNumberGenerator]
function New-Base64Secret { [Convert]::ToBase64String($rng::GetBytes(32)) }
function New-Password([int]$Length = 20) {
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_.:+'
    -join (1..$Length | ForEach-Object { $chars[$rng::GetInt32($chars.Length)] })
}
function New-Base32Secret {
    $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
    $data = $rng::GetBytes(20)
    $sb = [System.Text.StringBuilder]::new(); $buffer = 0; $bits = 0
    foreach ($b in $data) {
        $buffer = ($buffer -shl 8) -bor [int]$b; $bits += 8
        while ($bits -ge 5) { $bits -= 5; [void]$sb.Append($alphabet[($buffer -shr $bits) -band 31]) }
        $buffer = $buffer -band ((1 -shl $bits) - 1)
    }
    $sb.ToString()
}
# Replaces the value of KEY=... lines, keeps comments and order. Values with spaces get single quotes.
function Set-EnvValues([string[]]$Lines, [hashtable]$Values) {
    foreach ($line in $Lines) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=' -and $Values.ContainsKey($Matches[1])) {
            $key = $Matches[1]                      # keep it: the next -match overwrites $Matches
            $v = [string]$Values[$key]
            if ($v -match '[\s#]') { $v = "'" + $v + "'" }
            "$key=$v"
        } else { $line }
    }
}

Write-Step 'postgres password (the one you chose in the PostgreSQL installer)'
$sec = Read-Host -AsSecureString 'postgres password'
$pgPassword = [System.Net.NetworkCredential]::new('', $sec).Password
if ([string]::IsNullOrWhiteSpace($pgPassword)) { throw 'Empty password.' }
if ($pgPassword -match "[`"'#\s]") { Write-Note 'Your postgres password contains quotes, # or spaces - it is written in single quotes; if login fails, change it to letters/digits only.' }

$pgBin = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+$' } | Sort-Object { [int]$_.Name } -Descending | Select-Object -First 1
$pgBinPath = if ($pgBin) { Join-Path $pgBin.FullName 'bin' } else { 'C:\Program Files\PostgreSQL\18\bin' }
$models = Join-Path $RepoRoot 'ai-service\models'

$values = @{
    DB_PASSWORD               = New-Password
    DB_AI_PASSWORD            = New-Password
    PG_ADMIN_PASSWORD         = $pgPassword
    PG_BIN                    = $pgBinPath
    JWT_SECRET                = New-Base64Secret
    OTP_HMAC_KEY              = New-Base64Secret
    TOTP_ENC_KEY              = New-Base64Secret
    AI_SERVICE_JWT_SECRET     = New-Base64Secret
    STORAGE_ROOT              = (Join-Path $RepoRoot 'storage')
    YOLO_WEIGHTS              = (Join-Path $models 'yolov8s_civicbrain.onnx')
    MODELS_DIR                = $models
    TEXT_EMBEDDING_MODEL_DIR  = (Join-Path $models 'all-MiniLM-L6-v2')
    YOLO_CONFIG_DIR           = (Join-Path $RepoRoot 'ai-service\.ultralytics')
    WORKER_ID                 = "$($env:COMPUTERNAME.ToLower())-worker1"
}
$envLines = Set-EnvValues (Get-Content -LiteralPath (Join-Path $RepoRoot '.env.example') -Encoding UTF8) $values
[IO.File]::WriteAllLines($envFile, [string[]]$envLines, [Text.UTF8Encoding]::new($false))

$testValues = @{}
foreach ($k in 'ADMIN', 'OFFICER_ROAD', 'OFFICER_W3', 'CONTRACTOR', 'CONTRACTOR_OTHER', 'STAFF', 'CITIZEN1', 'CITIZEN2') {
    $testValues["E2E_$($k)_PASSWORD"] = New-Password
}
foreach ($k in 'ADMIN', 'OFFICER_ROAD', 'OFFICER_W3') { $testValues["E2E_$($k)_TOTP_SECRET"] = New-Base32Secret }
$testLines = Set-EnvValues (Get-Content -LiteralPath (Join-Path $RepoRoot '.env.test.example') -Encoding UTF8) $testValues
[IO.File]::WriteAllLines($envTestFile, [string[]]$testLines, [Text.UTF8Encoding]::new($false))
$pgPassword = $null

# self-check (values are not printed)
$check = Import-DotEnv -Path $envFile -NoProcessEnv
$left = @($check.Keys | Where-Object { $check[$_] -match 'REPLACE_WITH|change-me' })
if ($left.Count) { throw "Placeholders left in .env: $($left -join ', ')" }
$checkTest = Import-DotEnv -Path $envTestFile -NoProcessEnv
$leftTest = @($checkTest.Keys | Where-Object { $checkTest[$_] -match '^REPLACE_ME' })
if ($leftTest.Count) { throw "Placeholders left in .env.test: $($leftTest -join ', ')" }
Write-Ok ".env and .env.test written ($($check.Count) and $($checkTest.Count) keys). Secrets were not displayed."
Write-Host 'Next: pwsh -NoProfile -File scripts\dev\check-env.ps1' -ForegroundColor Green
