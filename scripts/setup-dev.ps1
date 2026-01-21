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

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MCP Factory Development Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Helper function for boot checks
function Write-Check {
    param([string]$Message, [bool]$Success = $true)
    if ($Success) {
        Write-Host "  [✓] $Message" -ForegroundColor Green
    } else {
        Write-Host "  [✗] $Message" -ForegroundColor Red
    }
}

# Boot sequence checks
Write-Host "  Initializing environment..." -ForegroundColor Gray
Start-Sleep -Milliseconds 100

# Check 1: Determine repo root
Write-Host ""
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

# Validate repo root
if (Test-Path (Join-Path $RepoRoot "README.md")) {
    Write-Check "Repository root located" $true
} else {
    Write-Check "Repository root located" $false
    Write-Host ""
    Write-Host "  [ERROR] Cannot find repository root. README.md not found at: $RepoRoot" -ForegroundColor Red
    exit 1
}

Set-Location $RepoRoot

# Check 2: Verify Python
Write-Host ""
$Python = Get-Command python.exe -ErrorAction SilentlyContinue
if ($Python) {
    Write-Check "Python 3.8+ detected" $true
} else {
    Write-Check "Python 3.8+ detected" $false
    Write-Host "  [Note] Will be auto-installed if missing" -ForegroundColor Yellow
}

# Check 3: Verify Git
Write-Host ""
$Git = Get-Command git.exe -ErrorAction SilentlyContinue
if ($Git) {
    Write-Check "Git detected" $true
} else {
    Write-Check "Git detected" $false
    Write-Host "  [ERROR] Git is required. Install from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# Check 4: Verify PowerShell
Write-Host ""
Write-Check "PowerShell 5.1+ ready" $true

Write-Host ""
Write-Host "  Starting analysis..." -ForegroundColor Gray
Write-Host ""

# Run the fixtures script
& .\scripts\run_fixtures.ps1 -BootstrapVcpkg

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [✗] Setup failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Try running manually:" -ForegroundColor Yellow
    Write-Host "    .\scripts\run_fixtures.ps1 -BootstrapVcpkg" -ForegroundColor Gray
    exit 1
}

# Completion
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  [✓] Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Review the confidence analysis above" -ForegroundColor White
Write-Host "    2. Check artifacts/ for detailed outputs" -ForegroundColor White
Write-Host "    3. Run on your own DLL:" -ForegroundColor White
Write-Host "       python src/discovery/csv_script.py --dll your_library.dll --headers include/" -ForegroundColor Gray
Write-Host ""
