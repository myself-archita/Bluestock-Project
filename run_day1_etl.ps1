param(
    [string]$RawDir = "data/raw"
)

$ErrorActionPreference = "Stop"

$python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path $python)) {
    throw "Bundled Python runtime not found at $python"
}

Write-Host "Running Day 1 ingestion audit..."
& $python data_ingestion.py --raw-dir $RawDir

Write-Host ""
Write-Host "Fetching live NAV snapshots..."
& $python live_nav_fetch.py --output-dir $RawDir

Write-Host ""
Write-Host "Day 1 ETL completed successfully."
