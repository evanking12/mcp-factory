#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Batch validation runner with tiered modes - Smoke / Core / Full

.DESCRIPTION
    Finds DLL/EXE files from PATH and System folders, validates each with debug_suite.py
    Three tiers available:
    - SMOKE (~10-30 files, <15s) - Quick validation for PRs/demos
    - CORE (~100-200 files, <30s) - Main branch CI/nightly (default)
    - FULL (466 files, ~60s) - Nightly/releases/sponsor demos

.PARAMETER Mode
    Validation tier: 'smoke', 'core', or 'full' (default: core)

.PARAMETER Limit
    Maximum number of files to process (optional)

.PARAMETER Glob
    Filter files by glob pattern (e.g., "System32\*.dll")

.PARAMETER Roots
    Custom search roots separated by semicolon (e.g., "C:\Windows\System32;C:\Program Files")

.EXAMPLE
    .\run_batch_validation.ps1
    
    Runs CORE tier (100-200 files, ~30s)

.EXAMPLE
    .\run_batch_validation.ps1 -Mode smoke
    
    Runs SMOKE tier (10-30 files, ~15s) for quick validation

.EXAMPLE
    .\run_batch_validation.ps1 -Mode full
    
    Runs FULL tier (466 files, ~60s) for comprehensive validation

.EXAMPLE
    .\run_batch_validation.ps1 -Mode smoke -Limit 50
    
    Smoke mode with max 50 files

.NOTES
    Requires: debug_suite.py in src/discovery/
    Output: Console with metrics at end
#>

param(
    [ValidateSet('smoke', 'core', 'full')]
    [string]$Mode = 'core',
    
    [int]$Limit = 0,
    
    [string]$Glob = '',
    
    [string]$Roots = ''
)

# Get script location and find debug_suite.py in src/discovery
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DebugSuite = Join-Path $ProjectRoot "src\discovery\debug_suite.py"

if (-not (Test-Path $DebugSuite)) {
    Write-Host "[ERROR] debug_suite.py not found at $DebugSuite" -ForegroundColor Red
    Write-Host "Expected location: src\discovery\debug_suite.py" -ForegroundColor Red
    exit 1
}

# Tier configurations
$TierConfig = @{
    'smoke' = @{ MaxFiles = 30; Description = 'Quick validation for PRs/demos' }
    'core'  = @{ MaxFiles = 200; Description = 'Main branch CI/nightly' }
    'full'  = @{ MaxFiles = 466; Description = 'Comprehensive (nightly/releases)' }
}

$MaxFilesToProcess = $TierConfig[$Mode].MaxFiles
if ($Limit -gt 0) {
    $MaxFilesToProcess = [Math]::Min($Limit, $MaxFilesToProcess)
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MCP FACTORY - BATCH VALIDATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Mode: $($Mode.ToUpper())" -ForegroundColor Yellow -NoNewline
Write-Host " - $($TierConfig[$Mode].Description)" -ForegroundColor Gray
Write-Host "Max files: $MaxFilesToProcess" -ForegroundColor Gray
Write-Host ""
Write-Host "Scanning PATH and System folders..." -ForegroundColor Gray
Write-Host ""

# Collections for results
$PassFiles = @()
$WarnFiles = @()
$ErrorFiles = @()
$SkippedFiles = @()
$AllFiles = @()
$FileTimes = @()

# Step 1: Find all DLL/EXE files
if ($Roots) {
    $SearchDirs = $Roots -split ';'
} else {
    $PathDirs = $env:PATH -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $SystemDirs = @(
        "C:\Windows\System32",
        "C:\Windows\SysWOW64",
        "C:\Program Files",
        "C:\Program Files (x86)"
    )
    $SearchDirs = $PathDirs + $SystemDirs | Where-Object { Test-Path $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

foreach ($Dir in $SearchDirs) {
    if ($AllFiles.Count -ge $MaxFilesToProcess) {
        break
    }
    
    try {
        if ($Glob) {
            $Files = @(Get-ChildItem -Path $Dir -Filter $Glob -ErrorAction SilentlyContinue)
        } else {
            $DllFiles = @(Get-ChildItem -Path $Dir -Filter "*.dll" -ErrorAction SilentlyContinue)
            $ExeFiles = @(Get-ChildItem -Path $Dir -Filter "*.exe" -ErrorAction SilentlyContinue)
            $Files = $DllFiles + $ExeFiles
        }
        $AllFiles += $Files
    } catch {
        # Silently skip folders we can't access
    }
}

# Deduplicate and limit
$AllFiles = $AllFiles | Select-Object -Unique -Property FullName | Select-Object -First $MaxFilesToProcess | ForEach-Object { $_.FullName }

Write-Host "Found $($AllFiles.Count) files to validate" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VALIDATION RESULTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$FileCount = 0
$TotalStartTime = Get-Date

# Step 2: Process each file
foreach ($FilePath in $AllFiles) {
    if (-not (Test-Path $FilePath)) {
        continue
    }

    $FileCount++
    $FileName = Split-Path -Leaf $FilePath
    
    $FileStartTime = Get-Date
    
    try {
        # Try to run debug_suite on the file
        $Output = & python $DebugSuite --file "$FilePath" 2>&1 | Out-String
        
        $FileElapsed = ((Get-Date) - $FileStartTime).TotalMilliseconds
        $FileTimes += @{ File = $FileName; Time = $FileElapsed; Status = 'processed' }
        
        # Parse output for status
        if ($Output -match "DEBUG SUITE PASSED") {
            Write-Host "[PASS] $FileName" -ForegroundColor Green
            $PassFiles += $FilePath
        }
        elseif ($Output -match "BREAKPOINT.*WARNING") {
            # Extract warning reason
            $WarningMatch = $Output -match "Issue: (.+)"
            $Reason = if ($WarningMatch) { 
                ($Output | Select-String "Issue: (.+)" | ForEach-Object { $_.Matches.Groups[1].Value })[0]
            } else {
                "See details"
            }
            if ($Reason) {
                Write-Host "[WARN] $FileName - $Reason" -ForegroundColor Yellow
            } else {
                Write-Host "[WARN] $FileName" -ForegroundColor Yellow
            }
            $WarnFiles += $FilePath
        }
        elseif ($Output -match "ERROR|FAILED" -or $Output -match "Traceback") {
            # Extract error reason
            $ErrorMatch = $Output | Select-String "Error:|FileNotFoundError:|Exception:" -First 1
            $Reason = if ($ErrorMatch) {
                $ErrorMatch.Line.Trim().Substring(0, [Math]::Min(60, $ErrorMatch.Line.Length))
            } else {
                "Unknown error (see logs)"
            }
            Write-Host "[ERROR] $FileName - $Reason" -ForegroundColor Red
            $ErrorFiles += @{ Path = $FilePath; Reason = $Reason; Output = $Output }
        }
        else {
            Write-Host "[PASS] $FileName" -ForegroundColor Green
            $PassFiles += $FilePath
        }
    }
    catch {
        # File couldn't be processed (locked, permission denied, etc.)
        $SkippedFiles += @{ Path = $FilePath; Reason = $_.Exception.Message }
    }
}

$TotalElapsed = ((Get-Date) - $TotalStartTime).TotalSeconds

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Files Processed: $FileCount" -ForegroundColor White

# Only show counts and descriptions for non-zero categories
if ($PassFiles.Count -gt 0) {
    Write-Host "  [PASS]    $($PassFiles.Count)" -ForegroundColor Green -NoNewline
    Write-Host " (file found and information parsed - confidence not reported here)" -ForegroundColor Gray
}

if ($WarnFiles.Count -gt 0) {
    Write-Host "  [WARN]    $($WarnFiles.Count)" -ForegroundColor Yellow -NoNewline
    Write-Host " (file analyzed but with degraded functionality - see details above)" -ForegroundColor Gray
}

if ($ErrorFiles.Count -gt 0) {
    Write-Host "  [ERROR]   $($ErrorFiles.Count)" -ForegroundColor Red -NoNewline
    Write-Host " (file analysis failed - see errors below)" -ForegroundColor Gray
}

if ($SkippedFiles.Count -gt 0) {
    Write-Host "  [SKIPPED] $($SkippedFiles.Count)" -ForegroundColor DarkYellow -NoNewline
    Write-Host " (file access denied or permission error - see details below)" -ForegroundColor Gray
}

Write-Host ""

# Show skipped files in orange
if ($SkippedFiles.Count -gt 0) {
    Write-Host "========================================" -ForegroundColor DarkYellow
    Write-Host "SKIPPED FILES (Permission/Access Issues)" -ForegroundColor DarkYellow
    Write-Host "========================================" -ForegroundColor DarkYellow
    foreach ($Item in $SkippedFiles) {
        $FileName = Split-Path -Leaf $Item.Path
        Write-Host "  [SKIPPED] $FileName - $($Item.Reason)" -ForegroundColor DarkYellow
    }
    Write-Host ""
}

# Show actual errors in red
if ($ErrorFiles.Count -gt 0) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERRORS (Validation Failures)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    foreach ($Item in $ErrorFiles) {
        $FileName = Split-Path -Leaf $Item.Path
        Write-Host "  [ERROR] $FileName" -ForegroundColor Red
        Write-Host "          Reason: $($Item.Reason)" -ForegroundColor Red
    }
    Write-Host ""
}

# Metrics
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "METRICS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$AvgTimeMs = if ($FileCount -gt 0) { [Math]::Round($TotalElapsed * 1000 / $FileCount, 1) } else { 0 }
$FailureCount = $ErrorFiles.Count + $SkippedFiles.Count

Write-Host "files_scanned=$FileCount" -ForegroundColor White
Write-Host "elapsed=$([Math]::Round($TotalElapsed, 1))s" -ForegroundColor White
Write-Host "avg=$($AvgTimeMs)ms/file" -ForegroundColor White
Write-Host "failures=$FailureCount" -ForegroundColor White

# Top 5 slowest files
if ($FileTimes.Count -gt 0) {
    $Top5 = $FileTimes | Sort-Object -Property Time -Descending | Select-Object -First 5
    if ($Top5.Count -gt 0) {
        Write-Host ""
        Write-Host "top5_slowest:" -ForegroundColor Gray
        foreach ($Item in $Top5) {
            Write-Host "  $($Item.File): $([Math]::Round($Item.Time, 1))ms" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

