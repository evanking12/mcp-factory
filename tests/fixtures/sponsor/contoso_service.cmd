@echo off
setlocal
if "%~1"=="--help" goto help
if "%~1"=="echo-sentinel" goto echo_sentinel
echo Contoso customer service command runner
exit /b 0

:help
echo Usage: contoso_service.cmd [--help] [echo-sentinel VALUE]
echo Commands:
echo   echo-sentinel VALUE    Echo a deterministic value for MCP E2E validation.
exit /b 0

:echo_sentinel
echo %~2
exit /b 0
