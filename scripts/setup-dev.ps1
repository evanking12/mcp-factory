#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete development environment setup for MCP Factory

.DESCRIPTION
    One-command initialization for new developers. Validates all prerequisites
    and bootstraps fixtures for immediate analysis capability.

.EXAMPLE
    .\scripts\setup-dev.ps1

.NOTES
    Requires PowerShell 5.1+ and Windows OS
#>

Write-Host "Setting up MCP Factory development environment..." -ForegroundColor Cyan
Write-Host ""

# Check Python 3.8+
Write-Host "Checking Python..." -NoNewline
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Error "Python not found. Install Python 3.8+ from https://python.org"
    exit 1
}
Write-Host " OK ($pythonCheck)" -ForegroundColor Green

# Check Visual Studio Build Tools (via dumpbin)
Write-Host "Checking dumpbin (VS Build Tools)..." -NoNewline
$dumpbinCheck = dumpbin /? 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " MISSING" -ForegroundColor Yellow
    Write-Warning "DUMPBIN not found. Install Visual Studio Build Tools:"
    Write-Warning "  https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022"
    Write-Warning "  (Can continue without it - PE parsing will be used as fallback)"
}

# Check Git
Write-Host "Checking Git..." -NoNewline
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVersion = git --version 2>&1
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " NOT FOUND" -ForegroundColor Yellow
    Write-Warning "Git not found. Install from https://git-scm.com"
    Write-Warning "  (Continuing anyway - Git required only for version control)"
}

Write-Host ""
Write-Host "Bootstrapping test fixtures..." -ForegroundColor Cyan

# Run fixture setup
& .\scripts\run_fixtures.ps1 -BootstrapVcpkg
if ($LASTEXITCODE -ne 0) {
    Write-Error "Fixture setup failed"
    exit 1
}

Write-Host ""
Write-Host "Running smoke test..." -ForegroundColor Cyan
& .\scripts\smoke_test.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Smoke test failed"
    exit 1
}

Write-Host ""
Write-Host "[OK] Development environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review README.md for quickstart"
Write-Host "  2. Run: python src\discovery\main.py --help"
Write-Host "  3. Try: python src\discovery\main.py --dll tests\fixtures\vcpkg_installed\x64-windows\bin\zstd.dll --headers tests\fixtures\vcpkg_installed\x64-windows\include"
Write-Host ""
