# One-command setup of the AI Assistant & Delivery Review module on a new Windows machine:
#
#     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
# Everything is installed inside this folder (storage\ and .venv\): a standalone Python (via uv), the
# pinned Python packages, the module's private Ollama model store, the embedding model and the demo
# database. Nothing is installed system-wide and no other module is touched.
# Needs: Windows 10/11, Ollama installed (https://ollama.com/download), internet on the first run.
# Optional: an NVIDIA GPU (the local model also runs on CPU, more slowly).
param(
    [string]$Model = "qwen2.5:7b-instruct",
    [string]$OllamaModelsFrom = "",  # optional: copy an existing Ollama "models" folder (offline handoff) instead of downloading
    [switch]$SkipTests
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # much faster downloads in Windows PowerShell 5.1
$root = Split-Path -Parent $PSScriptRoot
$storage = Join-Path $root "storage"
$uvVersion = "0.13.1"        # tested version
$pythonVersion = "3.12.15"   # tested version
function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Test-Port($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
# Runs a native tool. Tools write progress and warnings to stderr, which Windows PowerShell 5.1 can turn into
# terminating errors under "Stop" (when output is redirected), so only the exit code decides success.
function Invoke-Tool([string]$What, [string]$Exe, [string[]]$ArgList) {
    $ErrorActionPreference = "Continue"
    & $Exe @ArgList
    if ($LASTEXITCODE) { throw "$What failed (exit code $LASTEXITCODE)" }
}

Step "1/7 Prerequisites"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama is not installed. Install it from https://ollama.com/download, then run this script again."
}
Write-Host ("Ollama: " + (& { $ErrorActionPreference = "Continue"; ollama --version 2>$null }))
# Ollama's model loader cannot open files whose path exceeds 260 characters, even with Windows long paths
# enabled. The longest file is storage\ollama\models\blobs\sha256-<64 hex>, i.e. this folder's path + 100.
if ($root.Length + 100 -ge 260) {
    throw "This folder's path is too long ($($root.Length) characters, at most 159): the local model would fail to load. Move the folder somewhere shorter (e.g. C:\dev\module_assistant_delivery) and run this script again."
}
New-Item -ItemType Directory -Force (Join-Path $storage "tools") | Out-Null

Step "2/7 uv $uvVersion (Python manager), checksum-verified"
$uv = Join-Path $storage "tools\uv.exe"
if (-not (Test-Path $uv)) {
    $url = "https://github.com/astral-sh/uv/releases/download/$uvVersion/uv-x86_64-pc-windows-msvc.zip"
    $zip = Join-Path $storage "tools\uv.zip"
    Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
    Invoke-WebRequest "$url.sha256" -OutFile "$zip.sha256" -UseBasicParsing  # to a file: 5.1 returns this as raw bytes
    $expected = ((Get-Content "$zip.sha256" -Raw).Trim() -split "\s+")[0].ToLower()
    $actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) { Remove-Item $zip, "$zip.sha256"; throw "uv download failed its checksum check" }
    $unpacked = Join-Path $storage "tools\uv-$uvVersion"
    Expand-Archive $zip -DestinationPath $unpacked -Force
    Copy-Item (Get-ChildItem $unpacked -Recurse -Filter uv.exe | Select-Object -First 1).FullName $uv
    Remove-Item $zip, "$zip.sha256"
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $storage "python"
$env:UV_CACHE_DIR = Join-Path $storage "uv-cache"

Step "3/7 Python $pythonVersion and pinned packages (.venv)"
# uv keeps a minor-version link (cpython-3.12-...) to the installed Python. Copying the folder turns it into a
# real folder or a link to the old place, which uv then cannot replace: remove it and let uv re-create it.
# rmdir removes a link without touching its target.
Get-ChildItem (Join-Path $storage "python") -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^cpython-\d+\.\d+-' } | ForEach-Object {
        if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) { cmd.exe /c rmdir "$($_.FullName)" }
        else { Remove-Item $_.FullName -Recurse -Force }
    }
# --no-bin / --no-registry: no python3.12.exe in ~\.local\bin and no Windows registry entry (stays in this folder)
Invoke-Tool "Installing Python $pythonVersion" $uv @("python", "install", $pythonVersion, "--no-bin", "--no-registry")
# --managed-python: only the copy in storage\python, never an active/nearby .venv, PATH or registry Python
$python = "$(& { $ErrorActionPreference = "Continue"; & $uv python find $pythonVersion --managed-python 2>$null } | Select-Object -First 1)".Trim()
if (-not $python -or -not (Test-Path $python) -or -not $python.StartsWith($env:UV_PYTHON_INSTALL_DIR)) {
    throw "uv installed Python $pythonVersion but did not find it in storage\python (found: '$python')"
}
$venv = Join-Path $root ".venv"
$py = Join-Path $venv "Scripts\python.exe"
$cfg = Join-Path $venv "pyvenv.cfg"
if (Test-Path $cfg) {  # a .venv copied from another folder or machine still points at that folder's Python
    $venvHome = ((Get-Content $cfg | Where-Object { $_ -match "^home\s*=" } | Select-Object -First 1) -replace "^home\s*=\s*", "").Trim()
    if ($venvHome -ne (Split-Path -Parent $python)) {
        Write-Host ".venv was made for another location ($venvHome): re-creating it" -ForegroundColor Yellow
        Remove-Item $venv -Recurse -Force
    }
}
if (-not (Test-Path $py)) { Invoke-Tool "Creating .venv" $python @("-m", "venv", $venv) }
Invoke-Tool "Installing the Python packages" $py @("-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir",
    "--extra-index-url", "https://download.pytorch.org/whl/cpu", "-r", (Join-Path $root "backend\requirements.lock.txt"))

if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {  # zip handoffs ship the built UI; a Git clone does not
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "frontend\dist is missing: install Node.js 22+ (to build the UI) and run this script again" }
    Push-Location (Join-Path $root "frontend")
    try { Invoke-Tool "npm ci" "npm.cmd" @("ci", "--no-audit", "--no-fund"); Invoke-Tool "Building the UI" "npm.cmd" @("run", "build") } finally { Pop-Location }
}

Step "4/7 Configuration (.env)"
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "Created .env. Put your own Groq key after HOSTED_API_KEY= to enable delivery reviews and the fallback." -ForegroundColor Yellow
} else { Write-Host ".env already exists: left unchanged." }

Step "5/7 Local model $Model (module-private Ollama on port 11435)"
$models = Join-Path $storage "ollama\models"
New-Item -ItemType Directory -Force $models | Out-Null
if ($OllamaModelsFrom) {
    robocopy $OllamaModelsFrom $models /E /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Copying the Ollama models failed" }
}
$startedOllama = $false
if (-not (Test-Port 11435)) {
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start_ollama.ps1") -WindowStyle Minimized
    $startedOllama = $true
    for ($i = 0; $i -lt 60 -and -not (Test-Port 11435); $i++) { Start-Sleep -Seconds 1 }
    if (-not (Test-Port 11435)) { throw "The private Ollama did not start on port 11435" }
}
$env:OLLAMA_HOST = "127.0.0.1:11435"
Invoke-Tool "ollama pull $Model" "ollama" @("pull", $Model)

Step "6/7 Embedding model and demo data"
$env:HF_HOME = Join-Path $storage "hf"
$env:HF_HUB_DISABLE_XET = "1"          # plain HTTP downloads: the Xet path stalled on a slow network
$env:HF_HUB_DOWNLOAD_TIMEOUT = "60"
Push-Location (Join-Path $root "backend")
try {
    $ok = $false
    for ($attempt = 1; $attempt -le 3 -and -not $ok; $attempt++) {
        try { Invoke-Tool "Seeding" $py @("-m", "app.seed"); $ok = $true }
        catch { Write-Host "Seeding failed (attempt $attempt), retrying..." -ForegroundColor Yellow; Start-Sleep -Seconds 10 }
    }
    if (-not $ok) { throw "Downloading the embedding model / seeding the demo data failed" }

    Step "7/7 Checks"
    if (-not $SkipTests) { Invoke-Tool "Tests" $py @("-m", "pytest") }
} finally { Pop-Location }

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "Start the module with:  powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1"
if ($startedOllama) { Write-Host "(The private Ollama started by this setup keeps running in its own minimized window.)" }
