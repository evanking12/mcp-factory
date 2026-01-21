#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick setup for MCP Factory development

.DESCRIPTION
    One-liner setup: just run this script and it handles everything.
    - Auto-detects Python 3.8+
    - Auto-detects/bootstraps vcpkg
    - Auto-detects dumpbin.exe
    - Installs test fixtures (zstd + sqlite3)
    - Runs analysis with confidence scoring
    - Shows color-coded results

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\setup-dev.ps1

.NOTES
    Requires PowerShell 5.1+ and Windows OS
#>

# Set working directory to repo root
# Try multiple methods to find repo root (handles various invocation scenarios)
$RepoRoot = $null

# Method 1: Try via $PSCommandPath (standard invocation)
if ($PSCommandPath) {
    $scriptDir = Split-Path -Parent $PSCommandPath
    if ($scriptDir -match '\\scripts$') {
        $RepoRoot = Split-Path -Parent $scriptDir
    }
}

# Method 2: Try via $MyInvocation (fallback for & operator invocations)
if (-not $RepoRoot -and $MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if ($scriptDir -match '\\scripts$') {
        $RepoRoot = Split-Path -Parent $scriptDir
    }
}

# Method 3: Use current directory (last resort)
if (-not $RepoRoot) {
    $RepoRoot = Get-Location
}

# Validate we found a real repo root
if (-not (Test-Path (Join-Path $RepoRoot "README.md"))) {
    Write-Error "Cannot find repository root. Please ensure README.md exists in repo root directory."
    exit 1
}

Set-Location $RepoRoot

# Just run the fixtures script with bootstrap - it handles everything
& .\scripts\run_fixtures.ps1 -BootstrapVcpkg

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Setup failed. Try running manually:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_fixtures.ps1 -BootstrapVcpkg" -ForegroundColor Gray
    exit 1
}

# Show completion message
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Review the confidence analysis above" -ForegroundColor White
Write-Host "  2. Check artifacts/ for detailed outputs" -ForegroundColor White
Write-Host "  3. Run on your own DLL:" -ForegroundColor White
Write-Host "     python src/discovery/csv_script.py --dll your_library.dll --headers include/" -ForegroundColor Gray
Write-Host ""Write-Host ""
Write-Host "[OK] Development environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review README.md for quickstart"
Write-Host "  2. Run: python src\discovery\main.py --help"
Write-Host "  3. Try: python src\discovery\main.py --dll tests\fixtures\vcpkg_installed\x64-windows\bin\zstd.dll --headers tests\fixtures\vcpkg_installed\x64-windows\include"
Write-Host ""
