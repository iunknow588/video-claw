@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0status_local.ps1" %*
