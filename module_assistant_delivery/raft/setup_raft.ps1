# Separate training environment (CUDA torch + Unsloth). Kept apart from the service venv so training
# packages never change the running app. Uses the module's uv-managed CPython (see scripts/setup.ps1).
#
#     powershell -ExecutionPolicy Bypass -File raft\setup_raft.ps1            # exact versions of the lock file
#     powershell -ExecutionPolicy Bypass -File raft\setup_raft.ps1 -Latest    # newest Unsloth, then re-lock
param([switch]$Latest)
$ErrorActionPreference = "Stop"
$moduleRoot = Split-Path -Parent $PSScriptRoot
$storage = Join-Path $moduleRoot "storage"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $storage "python"
$env:UV_CACHE_DIR = Join-Path $storage "uv-cache"
$uv = Join-Path $storage "tools\uv.exe"
$lock = Join-Path $PSScriptRoot "requirements-raft.lock.txt"
# --managed-python: the copy in storage\python, never a nearby .venv, PATH or registry Python
$basePython = "$(& { $ErrorActionPreference = "Continue"; & $uv python find 3.12 --managed-python 2>$null } | Select-Object -First 1)".Trim()
$venv = Join-Path $moduleRoot ".venv-raft"
if (-not (Test-Path $venv)) { & $basePython -m venv $venv }
$py = Join-Path $venv "Scripts\python.exe"
$ErrorActionPreference = "Continue"  # pip writes progress to stderr; the exit code decides
if ($Latest) {
    # Unsloth's dependency tree requires the newest torch; the cu128 index stops at 2.11, so pip would
    # silently fall back to the CPU-only PyPI build. cu130 matches the installed driver (CUDA 13.x).
    & $py -m pip install --disable-pip-version-check unsloth
    & $py -m pip install --disable-pip-version-check --force-reinstall --no-deps "torch==2.14.1+cu130" "torchvision==0.29.1+cu130" --index-url https://download.pytorch.org/whl/cu130
} else {
    & $py -m pip install --disable-pip-version-check --extra-index-url https://download.pytorch.org/whl/cu130 -r $lock
}
if ($LASTEXITCODE) { throw "Installing the training packages failed" }
& $py -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
& $py -c "import unsloth, transformers, trl, peft, bitsandbytes; print('unsloth', unsloth.__version__, 'transformers', transformers.__version__, 'trl', trl.__version__, 'peft', peft.__version__, 'bnb', bitsandbytes.__version__)"
if ($Latest) { & $py -m pip freeze | Set-Content -Encoding utf8 $lock }
