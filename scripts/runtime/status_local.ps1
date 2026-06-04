param(
    [int]$Port = 8000
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

function Test-ReloadEnabled {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandLine
    )

    if (-not $CommandLine) {
        return $false
    }

    return $CommandLine.ToLowerInvariant().Contains("--reload")
}

$repoRoot = Resolve-RepoRoot
$listener = Get-ListeningProcessInfo -PortNumber $Port

if (-not $listener) {
    Write-Host "Status: stopped" -ForegroundColor Yellow
    Write-Host "Port: $Port"
    exit 0
}

$commandLine = ""
if ($null -ne $listener.CommandLine) {
    $commandLine = [string]$listener.CommandLine
}

$isRepoService = Test-IsRepoLocalService -RepoRoot $repoRoot -CommandLine $commandLine
$reloadEnabled = Test-ReloadEnabled -CommandLine $commandLine

Write-Host "Status: running" -ForegroundColor Green
Write-Host "Port: $($listener.LocalPort)"
Write-Host "PID: $($listener.OwningProcess)"
Write-Host "Process: $($listener.ProcessName)"
Write-Host "Repo service: $(if ($isRepoService) { 'yes' } else { 'no' })"
Write-Host "Reload: $(if ($reloadEnabled) { 'enabled' } else { 'disabled' })"
if ($commandLine) {
    Write-Host "Command: $commandLine" -ForegroundColor DarkCyan
}
