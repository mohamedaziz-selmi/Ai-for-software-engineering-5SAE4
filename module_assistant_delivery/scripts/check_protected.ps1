# Verifies that no protected (teammate/shared) file changed since docs/protected_baseline.sha256 was recorded.
# Read-only: hashes files, writes nothing.
$moduleRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Split-Path -Parent $moduleRoot
$baseline = Join-Path $moduleRoot "docs\protected_baseline.sha256"
# rag_service\chroma_db is the retrieval service's own runtime database: it rewrites its index files every
# time that service runs (not in Git), so it is skipped rather than reported on every run. The same holds for
# cerebro_business_ai\.runtime (its private Python, logs and state, created by its SETUP.cmd) and control_center\logs.
$skip = '\\(module_assistant_delivery|node_modules|\.venv|\.git)\\|\\rag_service\\chroma_db\\|\\cerebro_business_ai\\\.runtime\\|\\control_center\\logs\\'
$expected = @{}
foreach ($line in Get-Content $baseline -Encoding utf8) {
    if ($line.Length -gt 66 -and ("\" + $line.Substring(66)) -notmatch $skip) { $expected[$line.Substring(66)] = $line.Substring(0, 64) }
}
$current = @{}
Get-ChildItem $appRoot -Recurse -File -Force | Where-Object { $_.FullName -notmatch $skip } | ForEach-Object {
    $current[$_.FullName.Substring($appRoot.Length + 1)] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
}
$changed = @($expected.Keys | Where-Object { $current.ContainsKey($_) -and $current[$_] -ne $expected[$_] })
$missing = @($expected.Keys | Where-Object { -not $current.ContainsKey($_) })
$added = @($current.Keys | Where-Object { -not $expected.ContainsKey($_) })
"protected files in baseline: $($expected.Count); changed: $($changed.Count); missing: $($missing.Count); new: $($added.Count)"
$changed | ForEach-Object { "CHANGED  $_" }
$missing | ForEach-Object { "MISSING  $_" }
$added | ForEach-Object { "NEW      $_" }
if ($changed.Count -or $missing.Count) { exit 1 }
