#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run DLL export analysis on vcpkg-installed test fixtures (zstd + sqlite3)

.DESCRIPTION
    This script automates the testing workflow:
    1. Auto-detects or installs vcpkg (or accepts explicit path)
    2. Auto-detects dumpbin.exe from Visual Studio installations
    3. Installs test dependencies via vcpkg manifest mode (runs from tests/fixtures)
    4. Locates installed DLLs and headers
    5. Runs csv_script.py analysis on each fixture
    6. Verifies output files were generated

    The script is "drop-in" ready - it will automatically find vcpkg and dumpbin
    or bootstrap them if needed.

.PARAMETER VcpkgExe
    Path to vcpkg.exe. Optional - will auto-detect from PATH, 
    $env:USERPROFILE\Downloads\vcpkg, or repo-local vcpkg.

.PARAMETER Triplet
    Target triplet for vcpkg (default: x64-windows)

.PARAMETER OutDir
    Output directory for analysis results (default: artifacts)

.PARAMETER ScriptPath
    Path to the Python analysis script (default: src/discovery/csv_script.py)

.PARAMETER DumpbinExe
    Path to dumpbin.exe. Optional - will auto-detect from Visual Studio installations.

.PARAMETER BootstrapVcpkg
    If vcpkg is not found, automatically clone and bootstrap it to
    $env:USERPROFILE\Downloads\vcpkg

.PARAMETER NoBootstrap
    Skip Visual Studio environment bootstrapping (used internally to prevent recursion)

.PARAMETER InstallBuildToolsIfMissing
    Reserved for future use - does not auto-install Visual Studio Build Tools

.EXAMPLE
    .\scripts\run_fixtures.ps1
    
    Runs with full auto-detection of vcpkg and dumpbin

.EXAMPLE
    .\scripts\run_fixtures.ps1 -BootstrapVcpkg
    
    Auto-installs vcpkg if not found, then runs fixtures

.EXAMPLE
    .\scripts\run_fixtures.ps1 -VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe"

.EXAMPLE
    .\scripts\run_fixtures.ps1 -VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe" -Triplet x64-windows -OutDir "test_output"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$VcpkgExe = "",

    [Parameter(Mandatory = $false)]
    [string]$Triplet = "x64-windows",

    [Parameter(Mandatory = $false)]
    [string]$OutDir = "artifacts",

    [Parameter(Mandatory = $false)]
    [string]$ScriptPath = "src/discovery/csv_script.py",

    [Parameter(Mandatory = $false)]
    [string]$DumpbinExe = "",

    [Parameter(Mandatory = $false)]
    [switch]$NoBootstrap,

    [Parameter(Mandatory = $false)]
    [switch]$InstallBuildToolsIfMissing,

    [Parameter(Mandatory = $false)]
    [switch]$BootstrapVcpkg
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

function Resolve-DumpbinPath {
    <#
    .SYNOPSIS
        Robustly locates dumpbin.exe from various sources
    .DESCRIPTION
        Searches in priority order:
        1. User-provided -DumpbinExe parameter
        2. Current PATH (Get-Command)
        3. vswhere.exe query for all VS instances
        4. Fallback brute-force search in common VS locations
    .OUTPUTS
        Full path to dumpbin.exe, or $null if not found
    #>
    param(
        [string]$UserProvidedPath
    )

    # 1. User-provided path
    if ($UserProvidedPath -ne "") {
        if (Test-Path $UserProvidedPath) {
            Write-Host "[Detection] Using user-provided dumpbin: $UserProvidedPath" -ForegroundColor Cyan
            return $UserProvidedPath
        } else {
            Write-Error-Exit "Specified dumpbin not found: $UserProvidedPath"
        }
    }

    # 2. Check PATH
    Write-Host "[Detection] Checking PATH for dumpbin.exe..." -ForegroundColor Gray
    $PathDumpbin = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
    if ($PathDumpbin) {
        $DumpbinPath = $PathDumpbin.Source
        Write-Host "[Detection] Found dumpbin in PATH: $DumpbinPath" -ForegroundColor Cyan
        return $DumpbinPath
    }

    # 3. Try vswhere.exe
    Write-Host "[Detection] Searching via vswhere.exe..." -ForegroundColor Gray
    $VsWherePaths = @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe"
    )

    $VsWhereExe = $null
    foreach ($Path in $VsWherePaths) {
        if (Test-Path $Path) {
            $VsWhereExe = $Path
            break
        }
    }

    if ($VsWhereExe) {
        Write-Host "[Detection] Found vswhere.exe: $VsWhereExe" -ForegroundColor Gray
        
        # Query all VS instances with VC tools
        try {
            $VsInstances = & $VsWhereExe -all -products * `
                -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
                -property installationPath `
                -format value `
                2>$null

            foreach ($InstallPath in $VsInstances) {
                if ([string]::IsNullOrWhiteSpace($InstallPath)) { continue }
                
                Write-Host "[Detection]   Checking VS instance: $InstallPath" -ForegroundColor Gray
                
                # Find MSVC toolset directory
                $VcToolsDir = Join-Path $InstallPath "VC\Tools\MSVC"
                if (-not (Test-Path $VcToolsDir)) { continue }

                # Get all MSVC versions (sorted descending to get newest first)
                $MsvcVersions = Get-ChildItem -Path $VcToolsDir -Directory -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending

                foreach ($VersionDir in $MsvcVersions) {
                    $DumpbinCandidate = Join-Path $VersionDir.FullName "bin\Hostx64\x64\dumpbin.exe"
                    if (Test-Path $DumpbinCandidate) {
                        Write-Host "[Detection] Found dumpbin via vswhere: $DumpbinCandidate" -ForegroundColor Cyan
                        return $DumpbinCandidate
                    }
                }
            }
        } catch {
            Write-Host "[Detection]   vswhere query failed: $_" -ForegroundColor Yellow
        }
    }

    # 4. Fallback brute-force search
    Write-Host "[Detection] Fallback search in common VS locations..." -ForegroundColor Gray
    $VsBasePaths = @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio",
        "${env:ProgramFiles}\Microsoft Visual Studio"
    )

    foreach ($BasePath in $VsBasePaths) {
        if (-not (Test-Path $BasePath)) { continue }
        
        Write-Host "[Detection]   Searching in: $BasePath" -ForegroundColor Gray
        
        # Targeted search for VC\Tools\MSVC pattern to avoid full recursive scan
        $VcToolsPaths = Get-ChildItem -Path $BasePath -Filter "MSVC" -Recurse -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -like "*\VC\Tools\MSVC" } |
            Select-Object -First 5  # Limit to avoid slowness

        foreach ($VcToolsPath in $VcToolsPaths) {
            $MsvcVersions = Get-ChildItem -Path $VcToolsPath.FullName -Directory -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending

            foreach ($VersionDir in $MsvcVersions) {
                $DumpbinCandidate = Join-Path $VersionDir.FullName "bin\Hostx64\x64\dumpbin.exe"
                if (Test-Path $DumpbinCandidate) {
                    Write-Host "[Detection] Found dumpbin via fallback search: $DumpbinCandidate" -ForegroundColor Cyan
                    return $DumpbinCandidate
                }
            }
        }
    }

    Write-Host "[Detection] dumpbin.exe not found by any method" -ForegroundColor Yellow
    return $null
}

function Find-VsDevEnvironment {
    <#
    .SYNOPSIS
        Locates Visual Studio developer environment initialization scripts
    .OUTPUTS
        Hashtable with BatchFile and Architecture, or $null
    #>
    
    Write-Host "[Bootstrap] Searching for VS developer environment..." -ForegroundColor Gray
    
    # Try vswhere first
    $VsWherePaths = @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe"
    )

    $VsWhereExe = $null
    foreach ($Path in $VsWherePaths) {
        if (Test-Path $Path) {
            $VsWhereExe = $Path
            break
        }
    }

    if ($VsWhereExe) {
        try {
            $VsInstances = & $VsWhereExe -all -products * `
                -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
                -property installationPath `
                -format value `
                2>$null

            foreach ($InstallPath in $VsInstances) {
                if ([string]::IsNullOrWhiteSpace($InstallPath)) { continue }
                
                # Try VsDevCmd.bat first (more reliable)
                $VsDevCmd = Join-Path $InstallPath "Common7\Tools\VsDevCmd.bat"
                if (Test-Path $VsDevCmd) {
                    Write-Host "[Bootstrap] Found VsDevCmd.bat: $VsDevCmd" -ForegroundColor Cyan
                    return @{
                        BatchFile = $VsDevCmd
                        Architecture = "-arch=amd64 -host_arch=amd64"
                    }
                }

                # Fallback to vcvars64.bat
                $VcVars64 = Join-Path $InstallPath "VC\Auxiliary\Build\vcvars64.bat"
                if (Test-Path $VcVars64) {
                    Write-Host "[Bootstrap] Found vcvars64.bat: $VcVars64" -ForegroundColor Cyan
                    return @{
                        BatchFile = $VcVars64
                        Architecture = ""
                    }
                }
            }
        } catch {
            Write-Host "[Bootstrap]   vswhere query failed: $_" -ForegroundColor Yellow
        }
    }

    # Fallback manual search
    $CommonBatLocations = @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Enterprise\Common7\Tools\VsDevCmd.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
    )

    foreach ($BatPath in $CommonBatLocations) {
        if (Test-Path $BatPath) {
            Write-Host "[Bootstrap] Found VsDevCmd.bat: $BatPath" -ForegroundColor Cyan
            return @{
                BatchFile = $BatPath
                Architecture = "-arch=amd64 -host_arch=amd64"
            }
        }
    }

    return $null
}

function Invoke-WithVsEnvironment {
    <#
    .SYNOPSIS
        Re-invokes this script inside a VS developer environment
    #>
    param(
        [string]$BatchFile,
        [string]$Architecture,
        [hashtable]$OriginalParams
    )

    Write-Host "`n[Bootstrap] Attempting to bootstrap into VS developer environment..." -ForegroundColor Yellow
    Write-Host "[Bootstrap] Batch file: $BatchFile" -ForegroundColor Gray
    
    # Build command to re-invoke this script with all original parameters
    $ScriptPath = $PSCommandPath
    $ParamString = ""
    
    foreach ($Key in $OriginalParams.Keys) {
        $Value = $OriginalParams[$Key]
        if ($Value -is [switch] -or $Value -is [bool]) {
            if ($Value) {
                $ParamString += " -$Key"
            }
        } else {
            $ParamString += " -$Key `"$Value`""
        }
    }
    
    # Add NoBootstrap to prevent infinite recursion
    $ParamString += " -NoBootstrap"
    
    $CmdCommand = "call `"$BatchFile`" $Architecture && powershell.exe -ExecutionPolicy Bypass -NoProfile -File `"$ScriptPath`" $ParamString"
    
    Write-Host "[Bootstrap] Executing: cmd.exe /c `"$CmdCommand`"" -ForegroundColor Gray
    
    # Execute
    $Result = cmd.exe /c $CmdCommand
    
    # Propagate exit code
    exit $LASTEXITCODE
}

function Resolve-VcpkgExePath {
    <#
    .SYNOPSIS
        Robustly locates vcpkg.exe from various sources
    .DESCRIPTION
        Searches in priority order:
        1. User-provided -VcpkgExe parameter
        2. Current PATH (Get-Command)
        3. $env:USERPROFILE\Downloads\vcpkg\vcpkg.exe
        4. Repo-local vcpkg (../../vcpkg/vcpkg.exe)
    .OUTPUTS
        Full path to vcpkg.exe, or $null if not found
    #>
    param(
        [string]$UserProvidedPath,
        [string]$RepoRoot
    )

    # 1. User-provided path
    if ($UserProvidedPath -ne "") {
        if (Test-Path $UserProvidedPath) {
            Write-Host "[Detection] Using user-provided vcpkg: $UserProvidedPath" -ForegroundColor Cyan
            return $UserProvidedPath
        } else {
            Write-Error-Exit "Specified vcpkg.exe not found: $UserProvidedPath"
        }
    }

    # 2. Check PATH
    Write-Host "[Detection] Checking PATH for vcpkg.exe..." -ForegroundColor Gray
    $PathVcpkg = Get-Command vcpkg.exe -ErrorAction SilentlyContinue
    if ($PathVcpkg) {
        $VcpkgPath = $PathVcpkg.Source
        Write-Host "[Detection] Found vcpkg in PATH: $VcpkgPath" -ForegroundColor Cyan
        return $VcpkgPath
    }

    # 3. Check user Downloads folder (recommended location)
    Write-Host "[Detection] Checking `$env:USERPROFILE\Downloads\vcpkg..." -ForegroundColor Gray
    $DownloadsVcpkg = Join-Path $env:USERPROFILE "Downloads\vcpkg\vcpkg.exe"
    if (Test-Path $DownloadsVcpkg) {
        Write-Host "[Detection] Found vcpkg in Downloads: $DownloadsVcpkg" -ForegroundColor Cyan
        return $DownloadsVcpkg
    }

    # 4. Check repo-local vcpkg (only if repo root is determined)
    Write-Host "[Detection] Checking for repo-local vcpkg..." -ForegroundColor Gray
    if ($RepoRoot -and (Test-Path $RepoRoot)) {
        $RepoParent = Split-Path -Parent $RepoRoot
        $RepoLocalVcpkg = Join-Path $RepoParent "vcpkg\vcpkg.exe"
        if (Test-Path $RepoLocalVcpkg) {
            Write-Host "[Detection] Found repo-local vcpkg: $RepoLocalVcpkg" -ForegroundColor Cyan
            return $RepoLocalVcpkg
        }
    } else {
        Write-Host "[Detection] Skipping repo-local vcpkg check (repo root not yet determined)" -ForegroundColor Gray
    }

    Write-Host "[Detection] vcpkg.exe not found by any method" -ForegroundColor Yellow
    return $null
}

function Bootstrap-Vcpkg {
    <#
    .SYNOPSIS
        Clones and bootstraps vcpkg to user Downloads folder
    #>
    param(
        [string]$TargetDir = (Join-Path $env:USERPROFILE "Downloads\vcpkg")
    )

    Write-Host "`n[Bootstrap] Installing vcpkg to: $TargetDir" -ForegroundColor Yellow
    
    if (Test-Path $TargetDir) {
        Write-Host "[Bootstrap] Directory already exists, checking for vcpkg.exe..." -ForegroundColor Gray
        $ExistingExe = Join-Path $TargetDir "vcpkg.exe"
        if (Test-Path $ExistingExe) {
            Write-Success "vcpkg.exe already exists: $ExistingExe"
            return $ExistingExe
        }
    }

    # Check for git
    $GitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
    if (-not $GitCmd) {
        Write-Host "[ERROR] git.exe not found in PATH" -ForegroundColor Red
        Write-Host "Install git from: https://git-scm.com/download/win" -ForegroundColor Yellow
        return $null
    }

    try {
        # Clone vcpkg
        Write-Host "[Bootstrap] Cloning vcpkg repository..." -ForegroundColor Cyan
        $ParentDir = Split-Path -Parent $TargetDir
        if (-not (Test-Path $ParentDir)) {
            New-Item -Path $ParentDir -ItemType Directory -Force | Out-Null
        }

        Push-Location $ParentDir
        
        if (Test-Path $TargetDir) {
            Write-Host "[Bootstrap] Removing incomplete vcpkg directory..." -ForegroundColor Gray
            Remove-Item -Path $TargetDir -Recurse -Force
        }

        & git clone https://github.com/microsoft/vcpkg.git
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Host "[ERROR] git clone failed" -ForegroundColor Red
            return $null
        }

        # Bootstrap vcpkg
        Write-Host "[Bootstrap] Running bootstrap-vcpkg.bat..." -ForegroundColor Cyan
        Push-Location $TargetDir
        
        & .\bootstrap-vcpkg.bat -disableMetrics 2>&1 | Where-Object { $_ -notmatch 'See LICENSE|Downloading|Validating' }
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Pop-Location
            Write-Host "[ERROR] bootstrap-vcpkg.bat failed" -ForegroundColor Red
            return $null
        }

        Pop-Location
        Pop-Location

        $VcpkgExePath = Join-Path $TargetDir "vcpkg.exe"
        Write-Host "[Debug] Checking for vcpkg.exe at: $VcpkgExePath" -ForegroundColor DarkGray
        if (Test-Path $VcpkgExePath) {
            Write-Success "vcpkg bootstrapped successfully: $VcpkgExePath"
            Write-Host "[Debug] vcpkg.exe verified, returning path" -ForegroundColor DarkGray
            return $VcpkgExePath
        } else {
            Write-Host "[ERROR] vcpkg.exe not found after bootstrap at: $VcpkgExePath" -ForegroundColor Red
            return $null
        }
    } catch {
        Pop-Location -ErrorAction SilentlyContinue
        Write-Host "[ERROR] vcpkg bootstrap failed: $_" -ForegroundColor Red
        return $null
    }
}

#endregion

#region Step 0: Determine repo root

Write-Step "Determining repository root"

# Get the directory where this script is located
# Try multiple methods to handle various invocation patterns
$ScriptDir = $null
if ($PSCommandPath) {
    $ScriptDir = Split-Path -Parent $PSCommandPath
} elseif ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

# If we got a script directory, use it as anchor
if ($ScriptDir) {
    if ($ScriptDir -match '\\scripts$') {
        $RepoRoot = Split-Path -Parent $ScriptDir
    } else {
        # Check if we're in repo root already (has scripts folder)
        if (Test-Path (Join-Path $ScriptDir "scripts")) {
            $RepoRoot = $ScriptDir
        } else {
            # Try to go up one level
            $RepoRoot = Split-Path -Parent $ScriptDir
        }
    }
} else {
    # Last resort: use current location
    $RepoRoot = Get-Location
}

# Validate repo root by checking for key files
if (-not (Test-Path (Join-Path $RepoRoot "README.md"))) {
    Write-Error "Cannot determine repository root. Please run from repo root or scripts/ folder."
    exit 1
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

# Locate vcpkg.exe
Write-Step "Locating vcpkg.exe"

$VcpkgPath = Resolve-VcpkgExePath -UserProvidedPath $VcpkgExe -RepoRoot $RepoRoot

if (-not $VcpkgPath) {
    # vcpkg not found
    if ($BootstrapVcpkg) {
        Write-Host "`n[Bootstrap] vcpkg.exe not found, attempting to install..." -ForegroundColor Yellow
        $VcpkgPath = Bootstrap-Vcpkg
        
        if (-not $VcpkgPath) {
            Write-Host "`n[ERROR] Failed to bootstrap vcpkg" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please install vcpkg manually:" -ForegroundColor Yellow
            Write-Host "  1. git clone https://github.com/microsoft/vcpkg.git `$env:USERPROFILE\Downloads\vcpkg" -ForegroundColor White
            Write-Host "  2. cd `$env:USERPROFILE\Downloads\vcpkg" -ForegroundColor White
            Write-Host "  3. .\bootstrap-vcpkg.bat" -ForegroundColor White
            Write-Host ""
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "[ERROR] Could not locate vcpkg.exe" -ForegroundColor Red
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Cyan
        Write-Host "  1. Install vcpkg to recommended location:" -ForegroundColor White
        Write-Host "     git clone https://github.com/microsoft/vcpkg.git `$env:USERPROFILE\Downloads\vcpkg" -ForegroundColor White
        Write-Host "     cd `$env:USERPROFILE\Downloads\vcpkg" -ForegroundColor White
        Write-Host "     .\bootstrap-vcpkg.bat" -ForegroundColor White
        Write-Host ""
        Write-Host "  2. Or run this script with -BootstrapVcpkg to auto-install" -ForegroundColor White
        Write-Host "     .\scripts\run_fixtures.ps1 -BootstrapVcpkg" -ForegroundColor White
        Write-Host ""
        Write-Host "  3. Or specify -VcpkgExe explicitly:" -ForegroundColor White
        Write-Host "     .\scripts\run_fixtures.ps1 -VcpkgExe 'C:\path\to\vcpkg.exe'" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

Write-Success "Using vcpkg: $VcpkgPath"

# Determine VCPKG_ROOT (folder containing vcpkg.exe)
Write-Host "[Debug] Computing VCPKG_ROOT from path: $VcpkgPath" -ForegroundColor DarkGray
if ($VcpkgPath) {
    Write-Host "[Debug] VcpkgPath is not empty, proceeding with Split-Path" -ForegroundColor DarkGray
    $VcpkgRoot = Split-Path -Parent (Resolve-Path $VcpkgPath)
    Write-Host "[Debug] VCPKG_ROOT computed: $VcpkgRoot" -ForegroundColor DarkGray
    Write-Success "VCPKG_ROOT: $VcpkgRoot"
} else {
    Write-Host "[ERROR] VcpkgPath is empty after bootstrap attempt" -ForegroundColor Red
    Write-Host "[Debug] VcpkgPath variable is null or empty string" -ForegroundColor DarkGray
    exit 1
}

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

$DumpbinPath = Resolve-DumpbinPath -UserProvidedPath $DumpbinExe

if (-not $DumpbinPath) {
    # dumpbin not found, attempt bootstrap unless already bootstrapped
    if ($NoBootstrap) {
        # Already tried bootstrap, it didn't work
        Write-Host "`n[ERROR] Could not locate dumpbin.exe even after bootstrapping" -ForegroundColor Red
        Write-Host ""
        Write-Host "dumpbin.exe is part of the Microsoft Visual C++ Build Tools." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Cyan
        Write-Host "  1. Install 'Visual Studio Build Tools' with the 'Desktop development with C++' workload" -ForegroundColor White
        Write-Host "     Download: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor White
        Write-Host ""
        Write-Host "  2. Or specify -DumpbinExe explicitly:" -ForegroundColor White
        Write-Host "     .\scripts\run_fixtures.ps1 -VcpkgExe '...' -DumpbinExe 'C:\Path\To\dumpbin.exe'" -ForegroundColor White
        Write-Host ""
        Write-Host "  3. Or run from 'x64 Native Tools Command Prompt for VS 2022'" -ForegroundColor White
        Write-Host ""
        
        if ($InstallBuildToolsIfMissing) {
            Write-Host "Note: -InstallBuildToolsIfMissing was specified, but automatic installation" -ForegroundColor Yellow
            Write-Host "      is not implemented for safety. Please install manually." -ForegroundColor Yellow
            Write-Host ""
        }
        
        exit 1
    }
    
    # Try to bootstrap
    Write-Host ""
    Write-Host "[Bootstrap] dumpbin.exe not found in standard locations" -ForegroundColor Yellow
    Write-Host "[Bootstrap] Attempting to initialize Visual Studio developer environment..." -ForegroundColor Yellow
    
    $VsEnv = Find-VsDevEnvironment
    
    if ($VsEnv) {
        # Found VS environment, re-invoke script
        $OriginalParams = @{
            VcpkgExe = $VcpkgExe
            Triplet = $Triplet
            OutDir = $OutDir
            ScriptPath = $ScriptPath
        }
        if ($DumpbinExe -ne "") {
            $OriginalParams.DumpbinExe = $DumpbinExe
        }
        if ($InstallBuildToolsIfMissing) {
            $OriginalParams.InstallBuildToolsIfMissing = $true
        }
        
        Invoke-WithVsEnvironment -BatchFile $VsEnv.BatchFile `
                                  -Architecture $VsEnv.Architecture `
                                  -OriginalParams $OriginalParams
        # If we get here, bootstrap succeeded and script will continue in the child process
        exit 0
    } else {
        # No VS environment found
        Write-Host ""
        Write-Host "[ERROR] Could not locate Visual Studio developer environment for bootstrapping" -ForegroundColor Red
        Write-Host ""
        Write-Host "dumpbin.exe is part of the Microsoft Visual C++ Build Tools." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Cyan
        Write-Host "  1. Install 'Visual Studio Build Tools' with the 'Desktop development with C++' workload" -ForegroundColor White
        Write-Host "     Download: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor White
        Write-Host ""
        Write-Host "  2. Or specify -DumpbinExe explicitly:" -ForegroundColor White
        Write-Host "     .\scripts\run_fixtures.ps1 -VcpkgExe '...' -DumpbinExe 'C:\Path\To\dumpbin.exe'" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

Write-Success "Using dumpbin: $DumpbinPath"
Write-Host "[Debug] Dumpbin path verified: $DumpbinPath" -ForegroundColor DarkGray

#endregion

#region Step 2: Install dependencies via vcpkg

Write-Step "Installing vcpkg dependencies (zstd, sqlite3)"

Write-Host "Note: vcpkg manifest mode requires running from the manifest directory"
Write-Host "Changing to: $ManifestRoot"
Write-Host "Running: vcpkg install --triplet $Triplet --x-wait-for-lock"

try {
    # vcpkg manifest mode requires running from the directory containing vcpkg.json
    Push-Location $ManifestRoot
    
    & $VcpkgPath install `
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
Write-Host "[Debug] Fixture testing completed successfully" -ForegroundColor DarkGray
Write-Host ""

#endregion
