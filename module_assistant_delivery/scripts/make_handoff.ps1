# Builds the handoff package of this module: only its own work (code, docs, data, prebuilt UI, RAFT adapter
# and results, scripts, lock files). Excluded: environments (.venv*), downloaded models and caches
# (storage\), node_modules, local databases, logs and .env (your key stays on your machine).
# The receiver runs scripts\setup.ps1 once to re-create everything else.
#
#     powershell -ExecutionPolicy Bypass -File scripts\make_handoff.ps1 [-NoAdapter]
#
# Output: handoff\module_assistant_delivery\ (a clean copy) and handoff\module_assistant_delivery.zip
param([switch]$NoAdapter)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root "handoff"
$copy = Join-Path $outDir "module_assistant_delivery"
$zip = Join-Path $outDir "module_assistant_delivery.zip"

# The UI is shipped prebuilt, so the receiver does not need Node.js.
if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "frontend\dist is missing and npm is not available to build it" }
    Push-Location (Join-Path $root "frontend"); try { npm.cmd ci; npm.cmd run build } finally { Pop-Location }
}

if (Test-Path $outDir) { Remove-Item $outDir -Recurse -Force }
New-Item -ItemType Directory -Force $copy | Out-Null
$excludeDirs = @(".venv", ".venv-raft", "storage", "node_modules", "handoff", "__pycache__", ".pytest_cache", "unsloth_compiled_cache",
                 (Join-Path $root "raft\outputs"))
$excludeFiles = @(".env", "*.log", "*.pyc")
robocopy $root $copy /E /XD $excludeDirs /XF $excludeFiles /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Copy failed (robocopy exit $LASTEXITCODE)" }

if (-not $NoAdapter) {  # the trained RAFT adapter (needed only to rebuild the RAFT model); checkpoints are not copied
    $adapter = Join-Path $root "raft\outputs\qwen2.5-7b-raft\adapter"
    if (Test-Path $adapter) {
        robocopy $adapter (Join-Path $copy "raft\outputs\qwen2.5-7b-raft\adapter") /E /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Copying the adapter failed" }
    }
}

# Refuse to package anything that looks like a secret.
$leak = Get-ChildItem $copy -Recurse -File | Where-Object { $_.Length -lt 5MB } |
    Select-String -Pattern "gsk_[A-Za-z0-9]{20,}", "HOSTED_API_KEY=[A-Za-z0-9_\-]{10,}" -List  # Groq key format / filled-in key line
if ($leak) { $leak | ForEach-Object { Write-Host "Possible secret in $($_.Path)" -ForegroundColor Red }; Remove-Item $outDir -Recurse -Force; throw "Handoff aborted: possible secret found" }

$files = Get-ChildItem $copy -Recurse -File
$manifest = $files | ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.FullName.Substring($copy.Length + 1).Replace("\", "/") }
$manifest | Set-Content -Encoding utf8 (Join-Path $copy "HANDOFF_MANIFEST.sha256")
Compress-Archive -Path $copy -DestinationPath $zip -CompressionLevel Optimal
"{0} files, {1:n1} MB copied; zip {2:n1} MB -> {3}" -f $files.Count, (($files | Measure-Object Length -Sum).Sum / 1MB), ((Get-Item $zip).Length / 1MB), $zip
