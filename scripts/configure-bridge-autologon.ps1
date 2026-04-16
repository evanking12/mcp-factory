#Requires -Version 5.1
<#
.SYNOPSIS
Configures the Azure Windows VM to auto-logon and start the MCP Factory GUI bridge.

.DESCRIPTION
This is intended to be run through Azure VM Run Command as Administrator/SYSTEM.
It does not print the supplied password. The password is used only to reset
AutoLogon and the per-user scheduled task that must run in the interactive
desktop session for pywinauto GUI automation.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$User = "azureuser",
    [string]$Repo = "C:\mcp-factory",
    [string]$Python = "C:\Program Files\Python311\python.exe",
    [int]$Port = 8090,

    [Parameter(Mandatory = $true)]
    [string]$BridgeSecret
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BridgePy = Join-Path $Repo "scripts\gui_bridge.py"
$Launcher = Join-Path $Repo "scripts\_bridge_launcher.bat"
$TaskName = "MCP-Factory-Bridge-Interactive"

if (-not (Test-Path $Repo)) {
    throw "Repo path not found: $Repo"
}
if (-not (Test-Path $BridgePy)) {
    throw "Bridge file not found: $BridgePy"
}
if (-not (Test-Path $Python)) {
    throw "Python not found: $Python"
}

$launcherContent = @"
@echo off
set BRIDGE_SECRET=$BridgeSecret
set BRIDGE_PORT=$Port
cd /d $Repo
if not exist "$Repo\logs" mkdir "$Repo\logs"
echo [bridge] starting %DATE% %TIME% >> "$Repo\logs\bridge.log"
git fetch origin main
git reset --hard origin/main
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :$Port ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
timeout /t 2 /nobreak >nul
"$Python" "$BridgePy" >> "$Repo\logs\bridge.log" 2>&1
"@

[System.IO.File]::WriteAllText($Launcher, $launcherContent, [System.Text.Encoding]::ASCII)

$winlogon = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $winlogon -Name "AutoAdminLogon" -Value "1" -Type String
Set-ItemProperty -Path $winlogon -Name "ForceAutoLogon" -Value "1" -Type String
Set-ItemProperty -Path $winlogon -Name "DefaultUserName" -Value $User -Type String
Set-ItemProperty -Path $winlogon -Name "DefaultDomainName" -Value "." -Type String
Set-ItemProperty -Path $winlogon -Name "DefaultPassword" -Value $Password -Type String
Remove-ItemProperty -Path $winlogon -Name "AutoLogonCount" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $winlogon -Name "LegalNoticeCaption" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $winlogon -Name "LegalNoticeText" -ErrorAction SilentlyContinue

$oobePolicy = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\OOBE"
if (-not (Test-Path $oobePolicy)) {
    New-Item -Path $oobePolicy -Force | Out-Null
}
Set-ItemProperty -Path $oobePolicy -Name "DisablePrivacyExperience" -Value 1 -Type DWord

$oobeState = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OOBE"
if (-not (Test-Path $oobeState)) {
    New-Item -Path $oobeState -Force | Out-Null
}
Set-ItemProperty -Path $oobeState -Name "DisablePrivacyExperience" -Value 1 -Type DWord
Set-ItemProperty -Path $oobeState -Name "PrivacyConsentStatus" -Value 1 -Type DWord
Set-ItemProperty -Path $oobeState -Name "BypassNRO" -Value 1 -Type DWord

powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

schtasks.exe /Delete /TN $TaskName /F 2>$null | Out-Null
$taskRun = "`"$Launcher`""
schtasks.exe /Create /TN $TaskName /TR $taskRun /SC ONLOGON /RU "$env:COMPUTERNAME\$User" /RP $Password /RL HIGHEST /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks create failed with exit code $LASTEXITCODE"
}

$taskXml = (schtasks.exe /Query /TN $TaskName /XML ONE 2>&1) -join "`n"
if ($taskXml -notmatch "RestartOnFailure") {
    $taskXml = $taskXml -replace '</Settings>', @"
  <RestartOnFailure>
    <Interval>PT1M</Interval>
    <Count>99</Count>
  </RestartOnFailure>
</Settings>
"@
    $tmpXml = [System.IO.Path]::GetTempFileName() + ".xml"
    [System.IO.File]::WriteAllText($tmpXml, $taskXml, [System.Text.Encoding]::Unicode)
    schtasks.exe /Create /TN $TaskName /XML $tmpXml /RU "$env:COMPUTERNAME\$User" /RP $Password /F | Out-Null
    Remove-Item $tmpXml -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        throw "schtasks restart-on-failure update failed with exit code $LASTEXITCODE"
    }
}

$fwRule = Get-NetFirewallRule -DisplayName "MCP Bridge $Port" -ErrorAction SilentlyContinue
if (-not $fwRule) {
    New-NetFirewallRule -DisplayName "MCP Bridge $Port" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
}

Write-Output "Configured AutoLogon and bridge task '$TaskName' for $User on port $Port."
Write-Output "SessionId=1 is required for GUI automation; reboot the VM after configuration so AutoLogon starts the bridge in the interactive desktop."
$currentListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($currentListener) {
    $currentProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($currentListener.OwningProcess)" -ErrorAction SilentlyContinue
    if ($currentProcess) {
        Write-Output "Current bridge listener SessionId=$($currentProcess.SessionId); expected SessionId=1 after AutoLogon."
    }
}
Write-Output "Launcher: $Launcher"
