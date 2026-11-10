<#
.SYNOPSIS
    Runs the batch pipeline end to end: ERP -> bronze (ADLS) -> silver (Fabric) -> gold (dbt).

.DESCRIPTION
    1. Starts the ERP database and runs the plant simulator
    2. Extracts what changed into Parquet and uploads it to the data lake
    3. Waits while the silver notebooks run in Fabric (manual step)
    4. Builds and tests the gold layer with dbt on the Fabric Warehouse

    Requirements: Docker Desktop open, `az login` on the Azure subscription that owns the lake,
    and the variables FABRIC_SQL_HOST and AZURE_STORAGE_ACCOUNT set (or passed as parameters).
#>
param(
    [string]$StorageAccount = $env:AZURE_STORAGE_ACCOUNT,
    [string]$FabricSqlHost = $env:FABRIC_SQL_HOST,
    [string]$UploadPython = "A:\Lucas\idp-venv\Scripts\python.exe",
    [string]$DbtExe = "A:\Lucas\dbt-venv\Scripts\dbt.exe",
    [string]$FabricAzConfigDir = "A:\Lucas\azconfig-facens",
    [switch]$SkipSimulator
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Name (exit code $LASTEXITCODE)" }
}

if (-not $StorageAccount) { throw "Set AZURE_STORAGE_ACCOUNT or pass -StorageAccount." }
if (-not $FabricSqlHost) { throw "Set FABRIC_SQL_HOST or pass -FabricSqlHost." }

Invoke-Step "Start the ERP database" { docker compose up -d --wait erp-db }

if (-not $SkipSimulator) {
    Invoke-Step "Run the plant simulator" { docker compose run --rm --build simulator }
}

Invoke-Step "Extract changes to Parquet (bronze)" { docker compose run --rm --build extractor }

Invoke-Step "Upload bronze to the data lake" {
    & $UploadPython ingestion\upload.py --account $StorageAccount
}

Write-Host "`n==> Silver (manual step in Fabric)" -ForegroundColor Cyan
Write-Host "Open the workspace idp-dev and run, in this order:"
Write-Host "  1. 01_build_silver"
Write-Host "  2. 02_test_silver   (must end with: 0 failed)"
Write-Host "Stop the Spark sessions afterwards to free the trial capacity."
Read-Host "Press Enter when both notebooks have finished"

$previousConfigDir = $env:AZURE_CONFIG_DIR
try {
    $env:AZURE_CONFIG_DIR = $FabricAzConfigDir
    $env:FABRIC_SQL_HOST = $FabricSqlHost
    Invoke-Step "Build and test the gold layer (dbt)" {
        & $DbtExe build --project-dir dbt --profiles-dir dbt
    }
}
finally {
    $env:AZURE_CONFIG_DIR = $previousConfigDir
}

Write-Host "`nPipeline finished." -ForegroundColor Green
