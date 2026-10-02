# =============================================================================
# CivicBrain | scripts/dev/new-secret.ps1 - prints one new random secret for .env / .env.test
#   pwsh -NoProfile -File scripts\dev\new-secret.ps1                 # 32 bytes, base64 (JWT_SECRET, OTP_HMAC_KEY, TOTP_ENC_KEY, AI_SERVICE_JWT_SECRET)
#   pwsh -NoProfile -File scripts\dev\new-secret.ps1 -Kind base32    # 20 bytes, base32 (TOTP secrets in .env.test)
#   pwsh -NoProfile -File scripts\dev\new-secret.ps1 -Kind password  # 20-char password (test accounts, role passwords)
# Uses the OS cryptographic random generator. Copy the value into the file yourself.
# =============================================================================
[CmdletBinding()]
param(
    [ValidateSet('base64', 'base32', 'password')][string]$Kind = 'base64',
    [ValidateRange(16, 128)][int]$Bytes = 32
)
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

switch ($Kind) {
    'base64' {
        [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes($Bytes))
    }
    'base32' {
        $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
        $data = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(20)   # 160 bits = 32 base32 chars
        $sb = [System.Text.StringBuilder]::new()
        $buffer = 0; $bits = 0
        foreach ($b in $data) {
            $buffer = ($buffer -shl 8) -bor [int]$b; $bits += 8
            while ($bits -ge 5) { $bits -= 5; [void]$sb.Append($alphabet[($buffer -shr $bits) -band 31]) }
            $buffer = $buffer -band ((1 -shl $bits) - 1)   # keep only the unused bits (no Int32 overflow)
        }
        if ($bits -gt 0) { [void]$sb.Append($alphabet[($buffer -shl (5 - $bits)) -band 31]) }
        $sb.ToString()
    }
    'password' {
        # letters + digits + a few symbols that are safe in .env files and PowerShell (no quotes, #, $, `)
        $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_.:+'
        -join (1..20 | ForEach-Object { $chars[[System.Security.Cryptography.RandomNumberGenerator]::GetInt32($chars.Length)] })
    }
}
