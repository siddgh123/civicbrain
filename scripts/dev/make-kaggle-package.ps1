# =============================================================================
# CivicBrain | scripts/dev/make-kaggle-package.ps1 - one zip with the existing YOLO dataset + training scripts
#   pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1            # -> kaggle_upload\civicbrain-yolo.zip
#   pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1 -Force     # replace an older zip
# Zip layout (Kaggle unpacks it; the notebook finds the files with a search, so the dataset name is free):
#   yolo/data.yaml  yolo/images/{train,val,test}/...  yolo/labels/{train,val,test}/...  (+ DATASET_CARD.md,
#   dataset_sources.csv, class_definition.csv when they exist)
#   training/prepare_mvp_dataset.py  training/train_yolo_mvp.py  training/kaggle_train_mvp.ipynb
# Nothing in data\yolo is changed. kaggle_upload\ is git-ignored. Allowed for the agent (01-safety).
# Next (human, about 15 min + upload time): kaggle.com -> Datasets -> New Dataset -> upload the zip ->
#   title "civicbrain-yolo" -> Private -> Create; then follow the human step of prompts\P03_dataset_kaggle.md.
# =============================================================================
[CmdletBinding()]
param([switch]$Force, [string]$OutDir)
. "$PSScriptRoot\_common.ps1"
Assert-PowerShell7

$yolo = Join-Path $RepoRoot 'data\yolo'
$training = Join-Path $RepoRoot 'ai-service\training'
if (-not $OutDir) { $OutDir = Join-Path $RepoRoot 'kaggle_upload' }
$zipPath = Join-Path $OutDir 'civicbrain-yolo.zip'

Write-Step 'Checking data\yolo'
if (-not (Test-Path -LiteralPath (Join-Path $yolo 'data.yaml'))) { throw 'data\yolo\data.yaml not found - copy your dataset folder to data\yolo first (prompts\README.md, step 0).' }
$imgExt = @('.jpg', '.jpeg', '.png', '.bmp', '.webp')
$summary = @()
foreach ($split in 'train', 'val', 'test') {
    $imgDir = Join-Path $yolo "images\$split"
    $lblDir = Join-Path $yolo "labels\$split"
    if (-not (Test-Path -LiteralPath $imgDir)) { throw "missing folder data\yolo\images\$split" }
    $imgs = @(Get-ChildItem -LiteralPath $imgDir -File -Recurse | Where-Object { $imgExt -contains $_.Extension.ToLower() })
    $lbls = @(if (Test-Path -LiteralPath $lblDir) { Get-ChildItem -LiteralPath $lblDir -File -Recurse -Filter '*.txt' })
    $summary += [pscustomobject]@{ Split = $split; Images = $imgs.Count; LabelFiles = $lbls.Count }
}
$summary | Format-Table -AutoSize | Out-String | Write-Host
$totalImgs = ($summary | Measure-Object Images -Sum).Sum
$totalLbls = ($summary | Measure-Object LabelFiles -Sum).Sum
if ($totalImgs -eq 0) { throw 'No images found in data\yolo\images\{train,val,test}.' }
if ($totalLbls -eq 0) { throw 'No label files in data\yolo\labels - the images are not labelled. Run /run-prompt P03b (prompts\P03b_autolabel_fallback.md) first.' }
if ($totalLbls -lt [math]::Floor($totalImgs * 0.9)) { Write-Note "only $totalLbls label files for $totalImgs images - images without a label file train as background. prepare_mvp_dataset.py reports details." }

if (Test-Path -LiteralPath $zipPath) {
    if (-not $Force) { throw "$zipPath exists - add -Force to replace it." }
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Add-Type -AssemblyName 'System.IO.Compression'
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
$store = [System.IO.Compression.CompressionLevel]::NoCompression     # images are already compressed
$deflate = [System.IO.Compression.CompressionLevel]::Optimal
$count = 0
# FileMode.Create replaces an older zip (-Force) without deleting anything else
$zipStream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::ReadWrite)
$zip = [System.IO.Compression.ZipArchive]::new($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    function Add-ZipFile([string]$Source, [string]$EntryName) {
        $level = if ($imgExt -contains ([IO.Path]::GetExtension($Source).ToLower())) { $store } else { $deflate }
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $Source, $EntryName, $level)
        $script:count++
    }
    Write-Step "Writing $zipPath (this takes a few minutes for ~3,400 images)"
    Add-ZipFile (Join-Path $yolo 'data.yaml') 'yolo/data.yaml'
    foreach ($extra in 'DATASET_CARD.md', 'dataset_sources.csv', 'class_definition.csv') {
        $f = Join-Path $yolo $extra
        if (Test-Path -LiteralPath $f) { Add-ZipFile $f "yolo/$extra" }
    }
    $yoloFull = (Resolve-Path -LiteralPath $yolo).Path.TrimEnd('\') + '\'
    foreach ($sub in 'images', 'labels') {
        $dir = Join-Path $yolo $sub
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($split in 'train', 'val', 'test') {
            $splitDir = Join-Path $dir $split
            if (-not (Test-Path -LiteralPath $splitDir)) { continue }
            Get-ChildItem -LiteralPath $splitDir -File -Recurse | ForEach-Object {
                $rel = $_.FullName.Substring($yoloFull.Length).Replace('\', '/')
                Add-ZipFile $_.FullName "yolo/$rel"
            }
        }
    }
    foreach ($t in 'prepare_mvp_dataset.py', 'train_yolo_mvp.py', 'kaggle_train_mvp.ipynb') {
        $f = Join-Path $training $t
        if (-not (Test-Path -LiteralPath $f)) { throw "missing ai-service\training\$t" }
        Add-ZipFile $f "training/$t"
    }
} finally { $zip.Dispose(); $zipStream.Dispose() }

$mb = [math]::Round((Get-Item -LiteralPath $zipPath).Length / (1024 * 1024), 1)
Write-Ok "kaggle_upload\civicbrain-yolo.zip: $count files, $mb MB ($totalImgs images, $totalLbls label files)"
Write-Host @'
NEXT (human, in the browser):
 1. kaggle.com -> Create -> New Dataset -> drop kaggle_upload\civicbrain-yolo.zip -> title civicbrain-yolo -> Private -> Create.
 2. kaggle.com -> Create -> New Notebook -> File -> Import Notebook -> ai-service\training\kaggle_train_mvp.ipynb.
 3. Right panel: Add Input -> your dataset civicbrain-yolo; Settings: Accelerator GPU (T4 x2 or P100), Internet ON.
 4. Run the first 4 cells (check + 3-epoch timing, ~10 min). Then "Save Version" -> "Save & Run All (Commit)".
    Training continues on Kaggle when you close the browser (2-4 h).
'@ -ForegroundColor Yellow
