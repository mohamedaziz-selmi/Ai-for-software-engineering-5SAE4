param(
    [ValidateSet('Setup','Start','Stop','Check')][string]$Action='Setup',
    [ValidateRange(1024,65000)][int]$BasePort=8900,
    [switch]$NoBrowser,[switch]$SkipModelDownload,[switch]$NoStart
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$runtime=Join-Path $root '.runtime'
$pythonDir=Join-Path $runtime 'python'
$python=Join-Path $pythonDir 'python.exe'
$manifest=Join-Path $runtime 'processes.json'
$logs=Join-Path $runtime 'logs'
$model='gemma3:4b'
$ollamaUrl='http://127.0.0.1:11434'
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Run-Python([string[]]$PythonArgs) {
    & $python @PythonArgs
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE). See the output above." }
}
function Test-Url([string]$Url) {
    try { $r=Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3; return $r.StatusCode -eq 200 } catch { return $false }
}
function Find-Ollama {
    $found=Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $candidates=@((Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),(Join-Path $env:ProgramFiles 'Ollama\ollama.exe'))
    foreach ($candidate in $candidates) { if (Test-Path -LiteralPath $candidate) { return $candidate } }
    return $null
}
function Ensure-Ollama([bool]$Pull) {
    $exe=Find-Ollama
    if (!(Test-Url ($ollamaUrl+'/api/tags'))) {
        if (!$exe) { throw 'Ollama was not found. Install it from https://ollama.com/download/windows and rerun SETUP.cmd.' }
        Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'ollama.log') -RedirectStandardError (Join-Path $logs 'ollama.err.log') | Out-Null
        $ready=$false
        for ($i=0;$i -lt 30;$i++) { if (Test-Url ($ollamaUrl+'/api/tags')) { $ready=$true;break }; Start-Sleep -Seconds 1 }
        if (!$ready) { throw 'Ollama did not start. Open the Ollama application and rerun SETUP.cmd.' }
    }
    $tags=Invoke-RestMethod -Uri ($ollamaUrl+'/api/tags') -TimeoutSec 5
    if (@($tags.models | Where-Object { $_.name -eq $model -or $_.model -eq $model }).Count -gt 0) { Write-Host "Ollama model is ready: $model";return }
    if (!$Pull -or $SkipModelDownload) { Write-Warning 'gemma3:4b is not downloaded. Writing features need it. Run SETUP.cmd when ready.';return }
    if (!$exe) { throw 'Ollama is running, but its executable was not found. Run: ollama pull gemma3:4b, then SETUP.cmd.' }
    $existing=Get-CimInstance Win32_Process -Filter "Name = 'ollama.exe'" | Where-Object { $_.CommandLine -match 'pull\s+gemma3:4b' }
    if ($existing) { throw 'An Ollama pull for gemma3:4b is already running. Let it finish, then rerun SETUP.cmd. No duplicate download was started.' }
    Write-Host 'Downloading gemma3:4b through Ollama (about 3.3 GB). Interrupted pulls can be resumed by rerunning SETUP.cmd.'
    & $exe pull $model
    if ($LASTEXITCODE -ne 0) { throw 'Gemma download did not finish. Keep the files and rerun SETUP.cmd to resume.' }
    $tags=Invoke-RestMethod -Uri ($ollamaUrl+'/api/tags') -TimeoutSec 5
    if (@($tags.models | Where-Object { $_.name -eq $model -or $_.model -eq $model }).Count -eq 0) { throw 'Ollama did not report the requested model after download.' }
}
function Test-Owned($Entry) {
    $proc=Get-CimInstance Win32_Process -Filter "ProcessId = $($Entry.pid)" -ErrorAction SilentlyContinue
    if (!$proc) { return $false }
    return ($proc.ExecutablePath -ieq $python -and $proc.CommandLine.Contains([string]$Entry.token) -and $proc.CreationDate.ToUniversalTime().ToString('o') -eq $Entry.created)
}
function Stop-Cerebro {
    if (!(Test-Path -LiteralPath $manifest)) { Write-Host 'This package has no managed processes.';return }
    $entries=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    foreach ($entry in $entries) {
        if (Test-Owned $entry) { Stop-Process -Id $entry.pid -ErrorAction SilentlyContinue;Write-Host "Stopped $($entry.name)." }
        else { Write-Host "No matching managed process for $($entry.name); nothing else stopped." }
    }
    [IO.File]::WriteAllText($manifest,'[]')
    Write-Host 'Cerebro stopped. Ollama was left running.'
}
function Start-Cerebro {
    if (!(Test-Path -LiteralPath (Join-Path $runtime 'setup-complete.json'))) { throw 'Run SETUP.cmd once before START.cmd.' }
    if (Test-Path -LiteralPath $manifest) {
        $stored=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
        $active=@($stored | Where-Object { Test-Owned $_ })
        if ($active.Count -gt 0) { Write-Host 'This package is already running. Use CHECK.cmd or STOP.cmd first.';return }
    }
    for ($port=$BasePort;$port -le $BasePort+5;$port++) {
        if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is occupied. No process was stopped. Close the conflicting app, or run START.cmd -BasePort 18900." }
    }
    Ensure-Ollama $false
    $env:CEREBRO_HOST='127.0.0.1';$env:GATEWAY_PORT=[string]$BasePort;$env:FRAUD_SERVICE_PORT=[string]($BasePort+1);$env:JOB_DESCRIPTION_SERVICE_PORT=[string]($BasePort+2);$env:DEMAND_SERVICE_PORT=[string]($BasePort+3);$env:PRODUCT_LISTING_SERVICE_PORT=[string]($BasePort+4);$env:FRONTEND_PORT=[string]($BasePort+5)
    $env:LLM_PROVIDER='ollama';$env:LOCAL_LLM_MODEL=$model;$env:OLLAMA_BASE_URL=$ollamaUrl
    $threads=[string][math]::Max(1,[math]::Floor([Environment]::ProcessorCount/2))
    $env:OMP_NUM_THREADS=$threads;$env:OPENBLAS_NUM_THREADS=$threads;$env:MKL_NUM_THREADS=$threads
    $entries=@();$definitions=@(@('gateway','services.gateway',0),@('fraud','services.fraud.service',1),@('job','services.job.service',2),@('demand','services.demand.service',3),@('product','services.product.service',4))
    try {
        foreach ($item in $definitions) {
            $port=$BasePort+[int]$item[2];$token=$item[1]+':app'
            $p=Start-Process -FilePath $python -ArgumentList @('-m','uvicorn',$token,'--host','127.0.0.1','--port',[string]$port) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs ($item[0]+'.log')) -RedirectStandardError (Join-Path $logs ($item[0]+'.err.log')) -PassThru
            $proc=Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)"
            $entries+=[pscustomobject]@{name=$item[0];pid=$p.Id;token=$token;created=$proc.CreationDate.ToUniversalTime().ToString('o');port=$port}
            $entries|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $manifest
        }
        $frontPort=$BasePort+5
        $p=Start-Process -FilePath $python -ArgumentList @('portable/serve_frontend.py','--port',[string]$frontPort,'--gateway-port',[string]$BasePort) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'frontend.log') -RedirectStandardError (Join-Path $logs 'frontend.err.log') -PassThru
        $proc=Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)"
        $entries+=[pscustomobject]@{name='frontend';pid=$p.Id;token='portable/serve_frontend.py';created=$proc.CreationDate.ToUniversalTime().ToString('o');port=$frontPort}
        $entries|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $manifest
        foreach ($entry in $entries) {
            $url=if ($entry.name -eq 'frontend') { "http://127.0.0.1:$($entry.port)/" } else { "http://127.0.0.1:$($entry.port)/health" }
            $ok=$false
            for ($i=0;$i -lt 45;$i++) { if (Test-Url $url) { $ok=$true;break };Start-Sleep -Seconds 1 }
            if (!$ok) { throw "$($entry.name) did not become healthy. Read .runtime\logs\$($entry.name).err.log." }
        }
        Write-Host "Cerebro is ready: http://127.0.0.1:$frontPort/"
        if (!$NoBrowser) { Start-Process "http://127.0.0.1:$frontPort/" }
    } catch { Stop-Cerebro;throw }
}
function Verify-Bundle {
    $receipt=Join-Path $root 'release-manifest.json'
    if (!(Test-Path -LiteralPath $receipt)) { throw 'Missing release-manifest.json. Extract the complete ZIP before running SETUP.cmd.' }
    $items=(Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json).files
    foreach ($item in $items) {
        $target=[IO.Path]::GetFullPath((Join-Path $root $item.path))
        if (!$target.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid package path in manifest.' }
        if (!(Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $item.sha256) { throw "Package file is missing or damaged: $($item.path). Extract the ZIP again." }
    }
}
function Setup-Cerebro {
    if (![Environment]::Is64BitOperatingSystem) { throw 'This package requires 64-bit Windows.' }
    Verify-Bundle
    $drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($root))
    if ($drive.AvailableFreeSpace -lt 8GB) { throw 'Keep at least 8 GB free for the private runtime and Gemma download.' }
    $memory=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    Write-Host ('Detected RAM: {0:N1} GB. 16 GB is recommended for local generation; inference speed and GPU use depend on this PC.' -f ($memory/1GB))
    $lockFile=Join-Path $runtime 'setup.lock'
    try { $lock=[IO.File]::Open($lockFile,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) } catch { throw 'Setup is already running for this package. Let that window finish.' }
    try {
        if (!(Test-Path -LiteralPath $python)) {
            Write-Host 'Preparing private Python runtime...'
            New-Item -ItemType Directory -Path $pythonDir -Force|Out-Null
            Expand-Archive -LiteralPath (Join-Path $root 'installer/python-3.11.9-embed-amd64.zip') -DestinationPath $pythonDir -Force
        }
        $paths=@('python311.zip','.','Lib\site-packages','..\..','..\..\ai-service','import site')
        [IO.File]::WriteAllLines((Join-Path $pythonDir 'python311._pth'),$paths,[Text.Encoding]::ASCII)
        Write-Host 'Installing bundled Python dependencies (no downloads)...'
        Run-Python -PythonArgs @((Join-Path $root 'portable/bootstrap_pip.py'))
        Run-Python -PythonArgs @('-m','pip','install','--no-index','--find-links',(Join-Path $root 'installer/wheels'),'--only-binary=:all:','--no-warn-script-location','-r',(Join-Path $root 'portable/requirements-runtime.txt'))
        New-Item -ItemType Directory -Path (Join-Path $root 'data') -Force|Out-Null
        $threads=[string][math]::Max(1,[math]::Floor([Environment]::ProcessorCount/2));$env:OMP_NUM_THREADS=$threads;$env:OPENBLAS_NUM_THREADS=$threads
        Write-Host 'Verifying saved models, retrieval index and application imports...'
        Run-Python -PythonArgs @((Join-Path $root 'portable/verify_runtime.py'))
        Ensure-Ollama $true
        [pscustomobject]@{ready=$true;model=$model;verified_at_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $runtime 'setup-complete.json')
    } finally { $lock.Dispose() }
    if (!$NoStart) { Start-Cerebro }
}
try {
    switch ($Action) {
        'Setup' { Setup-Cerebro }
        'Start' { Start-Cerebro }
        'Stop' { Stop-Cerebro }
        'Check' {
            if (!(Test-Path -LiteralPath $python)) { throw 'Run SETUP.cmd first.' }
            Run-Python -PythonArgs @((Join-Path $root 'portable/verify_runtime.py'))
            Write-Host "Gateway: $(Test-Url "http://127.0.0.1:$BasePort/health")"
            Write-Host "Frontend: $(Test-Url "http://127.0.0.1:$($BasePort+5)/")"
            Ensure-Ollama $false
        }
    }
} catch { Write-Error $_;exit 1 }
