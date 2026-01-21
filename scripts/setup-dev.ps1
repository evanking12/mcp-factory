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
$dumpbinFound = $false
try {
    $dumpbinCheck = dumpbin /? 2>&1 | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
        $dumpbinFound = $true
    }
} catch {
    # dumpbin not available
}

if (-not $dumpbinFound) {
    Write-Host " NOT IN PATH" -ForegroundColor Yellow
    Write-Host "      (Can continue - VS environment will be detected automatically)" -ForegroundColor Gray
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

# Run fixture setup with bootstrap option
try {
    & .\scripts\run_fixtures.ps1 -BootstrapVcpkg
    if ($LASTEXITCODE -ne 0) {
        throw "Fixture setup failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host ""
    Write-Error "Fixture setup failed: $_"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Try running manually:" -ForegroundColor White
    Write-Host "     .\scripts\run_fixtures.ps1 -BootstrapVcpkg" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Or if you have Visual Studio Build Tools, use:" -ForegroundColor White
    Write-Host "     .\scripts\run_fixtures.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. For manual vcpkg setup, see README.md" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Running smoke test..." -ForegroundColor Cyan
try {
    & .\scripts\smoke_test.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host ""
    Write-Error "Smoke test failed: $_"
    Write-Host ""
    Write-Host "This may indicate a temporary issue. You can:" -ForegroundColor Yellow
    Write-Host "  1. Re-run fixtures: .\scripts\run_fixtures.ps1" -ForegroundColor White
    Write-Host "  2. Check artifacts/ directory for outputs" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "MCP Factory is ready! Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Explore the test outputs:" -ForegroundColor White
Write-Host "   Get-ChildItem artifacts/ | Select-Object Name, Length" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run analysis on your own DLL:" -ForegroundColor White
Write-Host "   python src/discovery/csv_script.py --dll your_library.dll --headers include/" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Read the documentation:" -ForegroundColor White
Write-Host "   Get-Content README.md" -ForegroundColor Gray
Write-Host ""Write-Host ""
Write-Host "[OK] Development environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review README.md for quickstart"
Write-Host "  2. Run: python src\discovery\main.py --help"
Write-Host "  3. Try: python src\discovery\main.py --dll tests\fixtures\vcpkg_installed\x64-windows\bin\zstd.dll --headers tests\fixtures\vcpkg_installed\x64-windows\include"
Write-Host ""
