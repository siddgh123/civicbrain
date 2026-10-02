# =============================================================================
# CivicBrain | scripts/dev/sync-claude.ps1 - copies the agent rules and skills from .agents/ into .claude/ (Claude Code)
#   pwsh -NoProfile -File scripts\dev\sync-claude.ps1           # HUMAN: once after any edit inside .agents/
#   pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check    # read-only (agent may run it): PASS when .claude/ is current
# .agents/ is the source for both tools (Antigravity reads it directly, Claude Code reads .claude/).
# - Rules 01-03 (always on) are imported by CLAUDE.md and are NOT copied.
# - Rules 10-50 -> .claude/rules/<name>.md; Antigravity "globs:" become Claude Code "paths:".
#   A rule without globs (trigger always_on / model_decision) loads in every session.
# - Skills -> .claude/skills/<name>/SKILL.md (+ any extra files), with an "argument-hint" line added.
# - Also checks that .claude/settings.json and CLAUDE.md exist and that settings.json is valid JSON.
# Never deletes anything: a stale file in .claude/ is reported so the human can remove it.
# =============================================================================
[CmdletBinding()]
param([switch]$Check)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7

$agentsDir = Join-Path $RepoRoot '.agents'
$claudeDir = Join-Path $RepoRoot '.claude'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$argumentHints = @{
    'run-prompt'  = '[P01-P30 or P03b]'
    'verify'      = '[backend|frontend|ai|smoke|db|all]'
    'phase-gate'  = '[D1-D7]'
    'start-phase' = '[D1-D7 or P0-P12]'
}

function Read-Text([string]$Path) {
    return ([System.IO.File]::ReadAllText($Path, $utf8)) -replace "`r`n", "`n"
}

# Splits "---`n<yaml>`n---`n<body>" into @{ Yaml = [string[]]; Body = [string] }. No frontmatter -> Yaml empty.
function Split-FrontMatter([string]$Text) {
    $m = [regex]::Match($Text, '\A---\n(?<yaml>.*?)\n---\n?(?<body>.*)\z', 'Singleline')
    if (-not $m.Success) { return @{ Yaml = @(); Body = $Text } }
    return @{ Yaml = @($m.Groups['yaml'].Value -split "`n"); Body = $m.Groups['body'].Value }
}

function Get-YamlValue([string[]]$Yaml, [string]$Key) {
    foreach ($line in $Yaml) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*:\s*(?<v>.*)$") { return $Matches['v'].Trim().Trim('"').Trim("'") }
    }
    return $null
}

function Get-FullPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path)   # also turns / into \ on Windows, so keys compare equal
}

function Get-RelPath([string]$Path) {
    return [System.IO.Path]::GetRelativePath($RepoRoot, $Path) -replace '\\', '/'
}

# ---------- build the expected .claude files: target path -> text ----------
$expected = [ordered]@{}

$ruleFiles = @(Get-ChildItem -LiteralPath (Join-Path $agentsDir 'rules') -Filter '*.md' -File | Sort-Object Name)
if ($ruleFiles.Count -eq 0) { throw "No rules found in .agents/rules - is this the CivicBrain folder?" }
foreach ($file in $ruleFiles) {
    if ($file.Name -match '^0[1-3]-') { continue }   # imported by CLAUDE.md
    $parts = Split-FrontMatter (Read-Text $file.FullName)
    $globs = Get-YamlValue $parts.Yaml 'globs'
    $note = "<!-- Generated from .agents/rules/$($file.Name) by scripts/dev/sync-claude.ps1. Edit the source, then run the script. -->`n"
    if ($globs) {
        $paths = @($globs -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        $yaml = "---`npaths:`n" + (($paths | ForEach-Object { "  - `"$_`"" }) -join "`n") + "`n---`n"
    } else {
        $yaml = ''
    }
    $expected[(Get-FullPath (Join-Path $claudeDir "rules/$($file.Name)"))] = $yaml + $note + $parts.Body.TrimStart("`n")
}

$skillDirs = @(Get-ChildItem -LiteralPath (Join-Path $agentsDir 'skills') -Directory | Sort-Object Name)
if ($skillDirs.Count -eq 0) { throw "No skills found in .agents/skills" }
foreach ($dir in $skillDirs) {
    foreach ($file in @(Get-ChildItem -LiteralPath $dir.FullName -File -Recurse)) {
        $rel = [System.IO.Path]::GetRelativePath($dir.FullName, $file.FullName)
        $target = Get-FullPath (Join-Path $claudeDir "skills/$($dir.Name)/$rel")
        if ($file.Name -ne 'SKILL.md') { $expected[$target] = Read-Text $file.FullName; continue }
        $parts = Split-FrontMatter (Read-Text $file.FullName)
        if ($parts.Yaml.Count -eq 0) { throw "$(Get-RelPath $file.FullName) has no frontmatter" }
        $yamlLines = [System.Collections.Generic.List[string]]::new()
        foreach ($l in $parts.Yaml) { $yamlLines.Add($l) }
        if (-not (Get-YamlValue $parts.Yaml 'argument-hint') -and $argumentHints.ContainsKey($dir.Name)) {
            $yamlLines.Add("argument-hint: `"$($argumentHints[$dir.Name])`"")
        }
        $note = "<!-- Generated from .agents/skills/$($dir.Name)/SKILL.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. Claude Code: shell, browser and model notes are in CLAUDE.md. -->`n"
        $expected[$target] = "---`n" + ($yamlLines -join "`n") + "`n---`n" + $note + $parts.Body.TrimStart("`n")
    }
}

# ---- Rule bodies: for always-on rules that were "model_decision" in .agents/, prepend a one-line "Apply only when" guard,
# so Claude Code (where rules without a `paths:` field load every session) can still skip them for unrelated prompts.
foreach ($file in $ruleFiles) {
    if ($file.Name -match '^0[1-3]-') { continue }
    $parts = Split-FrontMatter (Read-Text $file.FullName)
    $trigger = Get-YamlValue $parts.Yaml 'trigger'
    $desc    = Get-YamlValue $parts.Yaml 'description'
    if ($trigger -ne 'model_decision' -or -not $desc) { continue }
    $target  = Get-FullPath (Join-Path $claudeDir "rules/$($file.Name)")
    if (-not $expected.Contains($target)) { continue }
    # strip a leading "Apply when" so the guard doesn't read "Apply this rule only when: Apply when ..."
    $trimmed = $desc -replace '^\s*Apply\s+when\s+', ''
    $guard   = "> Apply this rule only when: $trimmed`n`n"
    $existing = $expected[$target]
    # insert the guard after the generated-from HTML comment line
    $expected[$target] = ($existing -replace "(?m)^(<!-- Generated .*? -->\n)", "`$1$guard")
    continue
}

# ---------- compare or write ----------
$fail = 0
foreach ($target in $expected.Keys) {
    $rel = Get-RelPath $target
    $want = $expected[$target]
    $have = if (Test-Path -LiteralPath $target) { Read-Text $target } else { $null }
    if ($have -ceq $want) { Write-Ok "$rel is current"; continue }
    if ($Check) {
        $why = if ($null -eq $have) { 'missing' } else { 'differs from .agents/' }
        Write-Bad "$rel $why - the human runs: pwsh -NoProfile -File scripts\dev\sync-claude.ps1"
        $fail++
        continue
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    [System.IO.File]::WriteAllText($target, $want, $utf8)
    Write-Ok "$rel written"
}

# stale generated files (source removed or renamed) - reported, never deleted
foreach ($sub in 'rules', 'skills') {
    $root = Join-Path $claudeDir $sub
    if (-not (Test-Path -LiteralPath $root)) { continue }
    foreach ($f in @(Get-ChildItem -LiteralPath $root -File -Recurse)) {
        if (-not $expected.Contains((Get-FullPath $f.FullName))) {
            Write-Note "$(Get-RelPath $f.FullName) has no source in .agents/ - remove it by hand if it is not yours"
        }
    }
}

# settings.json and CLAUDE.md are kit files (not generated) - check they exist and parse
$settings = Join-Path $claudeDir 'settings.json'
if (-not (Test-Path -LiteralPath $settings)) {
    Write-Bad ".claude/settings.json missing - copy it from the kit"; $fail++
} else {
    try {
        $json = Read-Text $settings | ConvertFrom-Json -ErrorAction Stop
        $deny = @($json.permissions.deny).Count
        Write-Ok ".claude/settings.json is valid JSON ($deny deny rules)"
    } catch {
        Write-Bad ".claude/settings.json is not valid JSON: $($_.Exception.Message)"; $fail++
    }
}
if (Test-Path -LiteralPath (Join-Path $RepoRoot 'CLAUDE.md')) { Write-Ok 'CLAUDE.md present' }
else { Write-Bad 'CLAUDE.md missing - copy it from the kit'; $fail++ }

if ($fail -gt 0) {
    Write-Bad "sync-claude: $fail problem(s)"
    exit 1
}
Write-Ok ("sync-claude: .claude/ is current ({0} files)" -f $expected.Count)
