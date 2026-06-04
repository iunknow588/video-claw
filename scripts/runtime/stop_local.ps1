param(
    [int]$Port = 8010,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Resolve-RepoRoot {
    $candidate = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $candidate ".git")) {
        return $candidate
    }

    $current = $candidate
    while ($current) {
        if (Test-Path (Join-Path $current ".git")) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    throw "Could not locate the repository root from $PSScriptRoot"
}

function Get-ListeningProcessInfo {
    param(
        [Parameter(Mandatory = $true)]
        [int]$PortNumber
    )

    $connection = Get-NetTCPConnection -State Listen -LocalPort $PortNumber -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $connection) {
        return $null
    }

    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    [pscustomobject]@{
        LocalAddress = $connection.LocalAddress
        LocalPort = $connection.LocalPort
        OwningProcess = $connection.OwningProcess
        ProcessName = if ($processInfo) { $processInfo.Name } else { "" }
        CommandLine = if ($processInfo) { $processInfo.CommandLine } else { "" }
    }
}

function Test-IsRepoLocalService {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$CommandLine
    )

    if (-not $CommandLine) {
        return $false
    }

    $normalizedRepoRoot = $RepoRoot.Replace("/", "\").ToLowerInvariant()
    $normalizedCommandLine = $CommandLine.Replace("/", "\").ToLowerInvariant()

    if ($normalizedCommandLine.Contains($normalizedRepoRoot)) {
        return $true
    }

    if ($normalizedCommandLine.Contains("-m uvicorn") -and $normalizedCommandLine.Contains("main:app") -and $normalizedCommandLine.Contains("--app-dir src")) {
        return $true
    }

    if ($normalizedCommandLine.Contains("src\main.py")) {
        return $true
    }

    return $false
}

$repoRoot = Resolve-RepoRoot
$listener = Get-ListeningProcessInfo -PortNumber $Port

if (-not $listener) {
    Write-Host "No listening process found on port $Port." -ForegroundColor Yellow
    exit 0
}

$commandLine = ""
if ($null -ne $listener.CommandLine) {
    $commandLine = [string]$listener.CommandLine
}
if (-not $Force -and -not (Test-IsRepoLocalService -RepoRoot $repoRoot -CommandLine $commandLine)) {
    Write-Host "Port $Port is occupied, but the process does not look like this repository's local service." -ForegroundColor Yellow
    Write-Host "PID: $($listener.OwningProcess)  Process: $($listener.ProcessName)" -ForegroundColor Yellow
    if ($commandLine) {
        Write-Host "Command: $commandLine" -ForegroundColor DarkYellow
    }
    Write-Host "Rerun with -Force if you really want to stop that process." -ForegroundColor Yellow
    exit 1
}

Write-Host "Stopping local service on port $Port (PID $($listener.OwningProcess))..." -ForegroundColor Cyan
if ($commandLine) {
    Write-Host "Command: $commandLine" -ForegroundColor DarkCyan
}

Stop-Process -Id $listener.OwningProcess -Force
Start-Sleep -Milliseconds 500

$remaining = Get-ListeningProcessInfo -PortNumber $Port
if ($remaining) {
    throw "Process on port $Port is still listening after stop attempt."
}

Write-Host "Local service on port $Port has been stopped." -ForegroundColor Green
