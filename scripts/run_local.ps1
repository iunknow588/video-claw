param(
    [switch]$PrepareOnly,
    [switch]$SkipInstall,
    [switch]$SkipMigrate,
    [switch]$UseProjectDatabase,
    [switch]$UseMainEntry,
    [switch]$NoReload,
    [switch]$StrictPort,
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [int]$PortSearchLimit = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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

function Ensure-FileFromTemplate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$TemplatePath
    )

    if (Test-Path $Path) {
        return
    }

    if (-not (Test-Path $TemplatePath)) {
        throw "Template file not found: $TemplatePath"
    }

    Copy-Item -LiteralPath $TemplatePath -Destination $Path
    Write-Host "Created $Path from template." -ForegroundColor Cyan
}

function Ensure-RuntimeDirectories {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $directories = @(
        "runtime",
        "runtime\logs",
        "runtime\media",
        "runtime\media\audio",
        "runtime\media\subtitles",
        "runtime\media\renders",
        "runtime\media\videos"
    )

    foreach ($relativePath in $directories) {
        $fullPath = Join-Path $Root $relativePath
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath | Out-Null
        }
    }
}

function Get-VenvPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root "src\.venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
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

function Resolve-AvailablePort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$RequestedPort,
        [Parameter(Mandatory = $true)]
        [int]$SearchLimit,
        [switch]$FailIfBusy
    )

    $currentPort = $RequestedPort
    for ($offset = 0; $offset -le $SearchLimit; $offset++) {
        $listener = Get-ListeningProcessInfo -PortNumber $currentPort
        if (-not $listener) {
            if ($currentPort -ne $RequestedPort) {
                Write-Host "Port $RequestedPort is busy; switched to available port $currentPort." -ForegroundColor Yellow
            }
            return $currentPort
        }

        Write-Host "Port $currentPort is already in use by PID $($listener.OwningProcess) $($listener.ProcessName)." -ForegroundColor Yellow
        if ($listener.CommandLine) {
            Write-Host "Command: $($listener.CommandLine)" -ForegroundColor DarkYellow
        }

        if ($FailIfBusy) {
            throw "Port $RequestedPort is unavailable. Rerun with -Port <new-port> or stop PID $($listener.OwningProcess)."
        }

        $currentPort++
    }

    throw "Could not find an available port in the range $RequestedPort-$($RequestedPort + $SearchLimit)."
}

function New-LocalVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $venvPath = Join-Path $Root ".venv"
    Write-Host "Creating virtual environment at $venvPath" -ForegroundColor Cyan
    & python -m venv $venvPath
    return (Join-Path $venvPath "Scripts\python.exe")
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$envPath = Join-Path $repoRoot ".env"
$envTemplatePath = Join-Path $repoRoot ".env.example"
Ensure-FileFromTemplate -Path $envPath -TemplatePath $envTemplatePath
Ensure-RuntimeDirectories -Root $repoRoot

$pythonExe = Get-VenvPython -Root $repoRoot
$createdVenv = $false

if (-not $pythonExe) {
    $pythonExe = New-LocalVenv -Root $repoRoot
    $createdVenv = $true
}

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

if (-not $SkipInstall) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -e ".[dev]"
}

if (-not $UseProjectDatabase) {
    $env:DATABASE_URL = "sqlite+aiosqlite:///runtime/local-dev.db"
    Write-Host "Using local SQLite database: $($env:DATABASE_URL)" -ForegroundColor Yellow
}

if (-not $SkipMigrate) {
    Write-Host "Running Alembic migrations..." -ForegroundColor Cyan
    & $pythonExe -m alembic -c alembic.ini upgrade head
}

$resolvedPort = Resolve-AvailablePort -RequestedPort $Port -SearchLimit $PortSearchLimit -FailIfBusy:$StrictPort

if ($PrepareOnly) {
    Write-Host "Preparation complete." -ForegroundColor Green
    Write-Host "Python: $pythonExe"
    Write-Host "Database: $(if ($UseProjectDatabase) { 'project .env / config' } else { $env:DATABASE_URL })"
    Write-Host "Port: $resolvedPort"
    Write-Host "Next: scripts\\run_local.cmd or .\\scripts\\run_local.ps1"
    exit 0
}

Write-Host "Starting local service at http://${BindHost}:${resolvedPort}" -ForegroundColor Green

if ($UseMainEntry) {
    if ($resolvedPort -ne $Port) {
        $env:SERVER_PORT = "$resolvedPort"
    }
    Write-Host "Mode: python src\\main.py" -ForegroundColor Cyan
    & $pythonExe src\main.py
    exit $LASTEXITCODE
}

$uvicornArgs = @(
    "-m", "uvicorn",
    "main:app",
    "--app-dir", "src",
    "--host", $BindHost,
    "--port", "$resolvedPort"
)

if (-not $NoReload) {
    $uvicornArgs += "--reload"
}

Write-Host "Mode: uvicorn main:app --app-dir src" -ForegroundColor Cyan
& $pythonExe @uvicornArgs
exit $LASTEXITCODE
