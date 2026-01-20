#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Smoke test to verify fixture test outputs

.DESCRIPTION
    Validates that the fixture test produced expected outputs:
    - Tier2 CSV files exist for both zstd and sqlite3
    - CSVs contain expected function prefixes
    - File sizes are within reasonable ranges

.PARAMETER ArtifactsDir
    Directory containing fixture test outputs (default: artifacts)

.EXAMPLE
    .\scripts\smoke_test.ps1

.EXAMPLE
    .\scripts\smoke_test.ps1 -ArtifactsDir "test_output"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ArtifactsDir = "artifacts"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== MCP-Factory Smoke Test ===" -ForegroundColor Cyan

$failed = $false

# Expected files
$expectedFiles = @(
    "zstd_tier2_api_zstd_fixture.csv",
    "zstd_tier4_api_zstd_fixture.csv",
    "zstd_tiers_zstd_fixture.md",
    "zstd_exports_raw.txt",
    "sqlite3_tier2_api_sqlite3_fixture.csv",
    "sqlite3_tier4_api_sqlite3_fixture.csv",
    "sqlite3_tiers_sqlite3_fixture.md",
    "sqlite3_exports_raw.txt"
)

# Check file existence
Write-Host "`nChecking file existence in '$ArtifactsDir'..." -ForegroundColor Yellow
foreach ($file in $expectedFiles) {
    $path = Join-Path $ArtifactsDir $file
    if (Test-Path $path) {
        $size = (Get-Item $path).Length
        Write-Host "  [OK] $file ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] MISSING: $file" -ForegroundColor Red
        $failed = $true
    }
}

# Check CSV content
Write-Host "`nVerifying CSV content..." -ForegroundColor Yellow

# ZSTD tier2 CSV
$zstdTier2 = Join-Path $ArtifactsDir "zstd_tier2_api_zstd_fixture.csv"
if (Test-Path $zstdTier2) {
    $zstdCount = (Select-String -Path $zstdTier2 -Pattern "ZSTD_" | Measure-Object).Count
    if ($zstdCount -ge 170) {
        Write-Host "  [OK] zstd_tier2: Found $zstdCount ZSTD_ functions (expected >=170)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] zstd_tier2: Only found $zstdCount ZSTD_ functions (expected >=170)" -ForegroundColor Red
        $failed = $true
    }
}

# SQLite3 tier2 CSV
$sqlite3Tier2 = Join-Path $ArtifactsDir "sqlite3_tier2_api_sqlite3_fixture.csv"
if (Test-Path $sqlite3Tier2) {
    $sqlite3Count = (Select-String -Path $sqlite3Tier2 -Pattern "sqlite3_" | Measure-Object).Count
    if ($sqlite3Count -ge 280) {
        Write-Host "  [OK] sqlite3_tier2: Found $sqlite3Count sqlite3_ functions (expected >=280)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] sqlite3_tier2: Only found $sqlite3Count sqlite3_ functions (expected >=280)" -ForegroundColor Red
        $failed = $true
    }
}

# File size sanity checks
Write-Host "`nVerifying file sizes..." -ForegroundColor Yellow
$sizeChecks = @{
    "zstd_tier2_api_zstd_fixture.csv" = @{ Min = 100KB; Max = 150KB }
    "sqlite3_tier2_api_sqlite3_fixture.csv" = @{ Min = 80KB; Max = 120KB }
}

foreach ($file in $sizeChecks.Keys) {
    $path = Join-Path $ArtifactsDir $file
    if (Test-Path $path) {
        $size = (Get-Item $path).Length
        $min = $sizeChecks[$file].Min
        $max = $sizeChecks[$file].Max
        if ($size -ge $min -and $size -le $max) {
            Write-Host "  [OK] $file size OK ($size bytes)" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] $file size unusual ($size bytes, expected $min-$max)" -ForegroundColor Yellow
        }
    }
}

# Summary
Write-Host ""
if ($failed) {
    Write-Host "[FAILED] SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host "Run: .\scripts\run_fixtures.ps1 -VcpkgExe <path>" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "[PASSED] SMOKE TEST PASSED" -ForegroundColor Green
    Write-Host "All expected outputs present and valid." -ForegroundColor Green
    exit 0
}
