#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run DLL export analysis on vcpkg-installed test fixtures (zstd + sqlite3)

.DESCRIPTION
    This script automates the testing workflow:
    1. Installs test dependencies via vcpkg manifest mode (runs from tests/fixtures)
    2. Locates installed DLLs and headers in vcpkg root
    3. Runs csv_script.py analysis on each fixture
    4. Verifies output files were generated

    Note: vcpkg manifest mode requires running 'vcpkg install' from the directory
    containing vcpkg.json. This script handles that automatically.

.PARAMETER VcpkgExe
    Path to vcpkg.exe. Required.

.PARAMETER Triplet
    Target triplet for vcpkg (default: x64-windows)

.PARAMETER OutDir
    Output directory for analysis results (default: artifacts)

.PARAMETER ScriptPath
    Path to the Python analysis script (default: src/discovery/csv_script.py)

.EXAMPLE
    .\scripts\run_fixtures.ps1 -VcpkgExe "C:\vcpkg\vcpkg.exe"

.EXAMPLE
    .\scripts\run_fixtures.ps1 -VcpkgExe "C:\vcpkg\vcpkg.exe" -Triplet x64-windows -OutDir "test_output"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VcpkgExe,

    [Parameter(Mandatory = $false)]
    [string]$Triplet = "x64-windows",

    [Parameter(Mandatory = $false)]
    [string]$OutDir = "artifacts",

    [Parameter(Mandatory = $false)]
    [string]$ScriptPath = "src/discovery/csv_script.py",

    [Parameter(Mandatory = $false)]
    [string]$DumpbinExe = ""
)

# Note: ScriptPath is relative to repo root
# Note: DumpbinExe can be empty; script will auto-detect

# Enable strict mode for better error detection
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

#region Helper Functions

function Write-Step {
    param([string]$Message)
    Write-Host "`n===> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error-Exit {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Test-PathExists {
    param(
        [string]$Path,
        [string]$Description
    )
    if (-not (Test-Path $Path)) {
        Write-Error-Exit "$Description not found: $Path"
    }
    Write-Success "Found $Description`: $Path"
}

#endregion

#region Step 0: Determine repo root

Write-Step "Determining repository root"

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $PSCommandPath

# Assume repo root is the parent of 'scripts' folder
if ($ScriptDir -match '\\scripts$') {
    $RepoRoot = Split-Path -Parent $ScriptDir
} else {
    # If not in scripts folder, assume current directory is repo root
    $RepoRoot = Get-Location
}

# Verify repo structure
if (-not (Test-Path (Join-Path $RepoRoot "README.md"))) {
    Write-Error-Exit "Could not determine repo root. Expected README.md at: $RepoRoot"
}

Write-Success "Repository root: $RepoRoot"

# Change to repo root for consistent paths
Set-Location $RepoRoot

#endregion

#region Step 1: Validate inputs

Write-Step "Validating inputs"

# Check vcpkg.exe exists
Test-PathExists -Path $VcpkgExe -Description "vcpkg.exe"

# Determine VCPKG_ROOT (folder containing vcpkg.exe)
$VcpkgRoot = Split-Path -Parent (Resolve-Path $VcpkgExe)
Write-Success "VCPKG_ROOT: $VcpkgRoot"

# Check Python script exists (path is relative to repo root)
$ScriptFullPath = Join-Path $RepoRoot $ScriptPath
Write-Host "Resolved script path: $ScriptFullPath"
Test-PathExists -Path $ScriptFullPath -Description "Python analysis script"

# Check manifest exists
$ManifestRoot = Join-Path $RepoRoot "tests\fixtures"
$ManifestFile = Join-Path $ManifestRoot "vcpkg.json"
Test-PathExists -Path $ManifestFile -Description "vcpkg manifest"

Write-Success "All inputs validated"

#endregion

#region Step 1.5: Locate or validate dumpbin.exe

Write-Step "Locating dumpbin.exe"

$DumpbinPath = ""

if ($DumpbinExe -ne "") {
    # User provided explicit path
    if (Test-Path $DumpbinExe) {
        $DumpbinPath = $DumpbinExe
        Write-Success "Using provided dumpbin: $DumpbinPath"
    } else {
        Write-Error-Exit "Specified dumpbin not found: $DumpbinExe"
    }
} else {
    # Attempt to auto-detect dumpbin.exe
    Write-Host "No -DumpbinExe specified, attempting auto-detection..."
    
    # Common Visual Studio 2022 installation paths
    $VsBasePaths = @(
        "C:\Program Files\Microsoft Visual Studio\2022\Community",
        "C:\Program Files\Microsoft Visual Studio\2022\Professional",
        "C:\Program Files\Microsoft Visual Studio\2022\Enterprise",
        "C:\Program Files\Microsoft Visual Studio\2022\BuildTools",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\Community",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\Professional",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\Enterprise",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
    )
    
    foreach ($BasePath in $VsBasePaths) {
        if (Test-Path $BasePath) {
            Write-Host "Searching in: $BasePath"
            $Found = Get-ChildItem -Path $BasePath -Filter "dumpbin.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($Found) {
                $DumpbinPath = $Found.FullName
                Write-Success "Auto-detected dumpbin: $DumpbinPath"
                break
            }
        }
    }
    
    if ($DumpbinPath -eq "") {
        Write-Host ""
        Write-Host "[ERROR] Could not locate dumpbin.exe" -ForegroundColor Red
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Yellow
        Write-Host "  1. Run this script from 'Visual Studio x64 Native Tools Command Prompt'" -ForegroundColor Yellow
        Write-Host "  2. Or specify -DumpbinExe explicitly:" -ForegroundColor Yellow
        Write-Host "     .\scripts\run_fixtures.ps1 -VcpkgExe '...' -DumpbinExe 'C:\Path\To\dumpbin.exe'" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

#endregion

#region Step 2: Install dependencies via vcpkg

Write-Step "Installing vcpkg dependencies (zstd, sqlite3)"

Write-Host "Note: vcpkg manifest mode requires running from the manifest directory"
Write-Host "Changing to: $ManifestRoot"
Write-Host "Running: vcpkg install --triplet $Triplet --x-wait-for-lock"

try {
    # vcpkg manifest mode requires running from the directory containing vcpkg.json
    Push-Location $ManifestRoot
    
    & $VcpkgExe install `
        --triplet $Triplet `
        --x-wait-for-lock

    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Error-Exit "vcpkg install failed with exit code $LASTEXITCODE"
    }
    
    Pop-Location
} catch {
    Pop-Location
    Write-Error-Exit "vcpkg install failed: $_"
}

Write-Success "vcpkg install completed successfully"

#endregion

#region Step 3: Locate installed DLLs and headers

Write-Step "Locating installed DLLs and headers"

# vcpkg manifest mode installs to vcpkg_installed/<triplet> in the manifest directory
$InstalledDir = Join-Path $ManifestRoot "vcpkg_installed\$Triplet"
Write-Host "Resolved installed directory: $InstalledDir"

$BinDir = Join-Path $InstalledDir "bin"
$HeadersDir = Join-Path $InstalledDir "include"

# Verify directories exist
Test-PathExists -Path $InstalledDir -Description "vcpkg installed directory"
Test-PathExists -Path $BinDir -Description "vcpkg bin directory"
Test-PathExists -Path $HeadersDir -Description "vcpkg include directory"

# Find zstd DLL (try both zstd.dll and libzstd.dll)
$ZstdDll = $null
$ZstdDllNames = @("zstd.dll", "libzstd.dll")
foreach ($DllName in $ZstdDllNames) {
    $TestPath = Join-Path $BinDir $DllName
    if (Test-Path $TestPath) {
        $ZstdDll = $TestPath
        break
    }
}

if (-not $ZstdDll) {
    Write-Error-Exit "zstd DLL not found. Tried: $($ZstdDllNames -join ', ') in $BinDir"
}
Write-Success "Found zstd DLL: $ZstdDll"

# Find sqlite3 DLL
$Sqlite3Dll = Join-Path $BinDir "sqlite3.dll"
Test-PathExists -Path $Sqlite3Dll -Description "sqlite3 DLL"

#endregion

#region Step 4: Create output directory

Write-Step "Setting up output directory"

# Ensure output directory is always relative to repo root
$OutDirPath = Join-Path $RepoRoot $OutDir
Write-Host "Output directory (relative to repo root): $OutDirPath"

if (-not (Test-Path $OutDirPath)) {
    New-Item -Path $OutDirPath -ItemType Directory -Force | Out-Null
    Write-Success "Created output directory: $OutDirPath"
} else {
    Write-Success "Output directory exists: $OutDirPath"
}

#endregion

#region Step 5: Run analysis on zstd

Write-Step "Running analysis on zstd DLL"

$ZstdDllBaseName = [System.IO.Path]::GetFileNameWithoutExtension($ZstdDll)

Write-Host "Command: python `"$ScriptFullPath`" --dll `"$ZstdDll`" --headers `"$HeadersDir`" --out `"$OutDirPath`" --tag zstd_fixture --dumpbin `"$DumpbinPath`""

try {
    python "$ScriptFullPath" `
        --dll "$ZstdDll" `
        --headers "$HeadersDir" `
        --out "$OutDirPath" `
        --tag "zstd_fixture" `
        --dumpbin "$DumpbinPath"

    if ($LASTEXITCODE -ne 0) {
        Write-Error-Exit "Python script failed for zstd with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error-Exit "Failed to run analysis on zstd: $_"
}

Write-Success "zstd analysis completed"

#endregion

#region Step 6: Run analysis on sqlite3

Write-Step "Running analysis on sqlite3 DLL"

Write-Host "Command: python `"$ScriptFullPath`" --dll `"$Sqlite3Dll`" --headers `"$HeadersDir`" --out `"$OutDirPath`" --tag sqlite3_fixture --dumpbin `"$DumpbinPath`""

try {
    python "$ScriptFullPath" `
        --dll "$Sqlite3Dll" `
        --headers "$HeadersDir" `
        --out "$OutDirPath" `
        --tag "sqlite3_fixture" `
        --dumpbin "$DumpbinPath"

    if ($LASTEXITCODE -ne 0) {
        Write-Error-Exit "Python script failed for sqlite3 with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error-Exit "Failed to run analysis on sqlite3: $_"
}

Write-Success "sqlite3 analysis completed"

#endregion

#region Step 7: Verify outputs

Write-Step "Verifying generated output files"

# Expected output files for zstd
$ZstdExpectedFiles = @(
    "${ZstdDllBaseName}_tier1_api_zstd_fixture.csv",
    "${ZstdDllBaseName}_tier2_api_zstd_fixture.csv",
    "${ZstdDllBaseName}_tier4_api_zstd_fixture.csv",
    "${ZstdDllBaseName}_tiers_zstd_fixture.md",
    "${ZstdDllBaseName}_exports_raw.txt"
)

# Expected output files for sqlite3
$Sqlite3ExpectedFiles = @(
    "sqlite3_tier1_api_sqlite3_fixture.csv",
    "sqlite3_tier2_api_sqlite3_fixture.csv",
    "sqlite3_tier4_api_sqlite3_fixture.csv",
    "sqlite3_tiers_sqlite3_fixture.md",
    "sqlite3_exports_raw.txt"
)

$AllExpectedFiles = $ZstdExpectedFiles + $Sqlite3ExpectedFiles
$MissingFiles = @()
$FoundFiles = @()

foreach ($File in $AllExpectedFiles) {
    $FilePath = Join-Path $OutDirPath $File
    if (Test-Path $FilePath) {
        $FoundFiles += $FilePath
    } else {
        $MissingFiles += $File
    }
}

if ($MissingFiles.Count -gt 0) {
    Write-Host "`nWarning: Some expected files were not found:" -ForegroundColor Yellow
    foreach ($File in $MissingFiles) {
        Write-Host "  - $File" -ForegroundColor Yellow
    }
}

#endregion

#region Step 8: Summary

Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "FIXTURE TEST COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host ("=" * 70) -ForegroundColor Cyan

Write-Host "`nGenerated files in $OutDirPath`:" -ForegroundColor White
Write-Host ""

# Group files by fixture
Write-Host "ZSTD Fixture:" -ForegroundColor Cyan
foreach ($File in $ZstdExpectedFiles) {
    $FilePath = Join-Path $OutDirPath $File
    if (Test-Path $FilePath) {
        $Size = (Get-Item $FilePath).Length
        Write-Host ("  [OK] {0,-50} ({1,10:N0} bytes)" -f $File, $Size) -ForegroundColor Green
    } else {
        Write-Host ("  [--] {0,-50} (not found)" -f $File) -ForegroundColor Yellow
    }
}

Write-Host "`nSQLite3 Fixture:" -ForegroundColor Cyan
foreach ($File in $Sqlite3ExpectedFiles) {
    $FilePath = Join-Path $OutDirPath $File
    if (Test-Path $FilePath) {
        $Size = (Get-Item $FilePath).Length
        Write-Host ("  [OK] {0,-50} ({1,10:N0} bytes)" -f $File, $Size) -ForegroundColor Green
    } else {
        Write-Host ("  [--] {0,-50} (not found)" -f $File) -ForegroundColor Yellow
    }
}

Write-Host ""

#endregion

#region Step 9: Sanity check

Write-Step "Running sanity checks on generated CSVs"

# Check zstd CSV for ZSTD_ exports
$ZstdCsv = Join-Path $OutDirPath "${ZstdDllBaseName}_tier1_api_zstd_fixture.csv"
if (Test-Path $ZstdCsv) {
    $ZstdContent = Get-Content $ZstdCsv -Raw
    $ZstdMatches = ([regex]::Matches($ZstdContent, 'ZSTD_')).Count
    if ($ZstdMatches -gt 0) {
        Write-Success "zstd CSV contains $ZstdMatches 'ZSTD_' entries"
    } else {
        Write-Host "[WARN] zstd CSV contains no 'ZSTD_' entries" -ForegroundColor Yellow
    }
}

# Check sqlite3 CSV for sqlite3_ exports
$Sqlite3Csv = Join-Path $OutDirPath "sqlite3_tier1_api_sqlite3_fixture.csv"
if (Test-Path $Sqlite3Csv) {
    $Sqlite3Content = Get-Content $Sqlite3Csv -Raw
    $Sqlite3Matches = ([regex]::Matches($Sqlite3Content, 'sqlite3_')).Count
    if ($Sqlite3Matches -gt 0) {
        Write-Success "sqlite3 CSV contains $Sqlite3Matches 'sqlite3_' entries"
    } else {
        Write-Host "[WARN] sqlite3 CSV contains no 'sqlite3_' entries" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "All checks complete!" -ForegroundColor Green
Write-Host ""

#endregion
