@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1

if /I "%~1"=="stop" (
  shift
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_local.ps1" %*
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="status" (
  shift
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0status_local.ps1" %*
  exit /b %ERRORLEVEL%
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_local.ps1" %*
