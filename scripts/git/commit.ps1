param(
    [string]$Message,
    [switch]$NoPush
)

# =============================================================================
# Config
# =============================================================================
$script:RepoRootOverride = ""
$script:RepoSshUrl = "git@github.com:iunknow588/video-claw.git"
$script:RepoHttpsUrl = "https://github.com/iunknow588/video-claw.git"
$script:PreferredRemoteUrl = $script:RepoSshUrl

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-EnvFileValues {
    param(
        [string]$EnvPath
    )

    $values = @{}
    if (-not (Test-Path $EnvPath)) {
        return $values
    }

    foreach ($line in Get-Content -Path $EnvPath -ErrorAction SilentlyContinue) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed -match '^(?<key>[^=]+?)\s*=\s*(?<value>.*)$') {
            $key = $Matches['key'].Trim()
            $value = $Matches['value'].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $values[$key] = $value
        }
    }

    return $values
}

function Load-RepoUrlsFromEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $envPath = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $envPath)) {
        return
    }

    $envValues = Get-EnvFileValues -EnvPath $envPath
    if ($envValues.ContainsKey("REPO_ROOT_OVERRIDE")) {
        $script:RepoRootOverride = $envValues["REPO_ROOT_OVERRIDE"]
    }
    if ($envValues.ContainsKey("REPO_SSH_URL")) {
        $script:RepoSshUrl = $envValues["REPO_SSH_URL"]
    }
    if ($envValues.ContainsKey("REPO_HTTPS_URL")) {
        $script:RepoHttpsUrl = $envValues["REPO_HTTPS_URL"]
    }
    if ($envValues.ContainsKey("PREFERRED_REMOTE_URL")) {
        $script:PreferredRemoteUrl = $envValues["PREFERRED_REMOTE_URL"]
    }
}

# =============================================================================
# Helpers
# =============================================================================
function Resolve-RepoRoot {
    param(
        [switch]$CreateIfMissing
    )

    if ($RepoRootOverride) {
        if (-not (Test-Path $RepoRootOverride)) {
            throw "Configured RepoRootOverride does not exist: $RepoRootOverride"
        }
        return $RepoRootOverride
    }

    $defaultRoot = Split-Path -Parent $PSScriptRoot
    $candidates = @()
    if ($PWD -and $PWD.Path) {
        $candidates += $PWD.Path
    }
    if ($defaultRoot) {
        $candidates += $defaultRoot
    }

    foreach ($start in $candidates | Select-Object -Unique) {
        $current = $start
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
    }

    if ($CreateIfMissing) {
        if (-not $defaultRoot -or -not (Test-Path $defaultRoot)) {
            throw "Could not determine the default repository root from the script path."
        }
        return $defaultRoot
    }

    throw "Could not find a .git directory from current path or script path. Set `$RepoRootOverride or clone the repo first."
}

function Initialize-RepositoryIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    if (Test-Path (Join-Path $Root ".git")) {
        return $false
    }

    Write-Host "No .git directory found. Initializing a repository in $Root" -ForegroundColor Yellow
    git -C $Root init | Out-Null
    git -C $Root branch -M main 2>$null | Out-Null
    return $true
}

function Ensure-OriginRemote {
    $remoteNames = @(git remote)
    $hasOrigin = $remoteNames -contains "origin"

    if ($hasOrigin) {
        git remote set-url origin $PreferredRemoteUrl
        git remote set-url --push origin $PreferredRemoteUrl
        Write-Host "Updated origin -> $PreferredRemoteUrl" -ForegroundColor Cyan
    } else {
        git remote add origin $PreferredRemoteUrl
        Write-Host "Added origin -> $PreferredRemoteUrl" -ForegroundColor Cyan
    }
}

# =============================================================================
# Main
# =============================================================================
$root = Resolve-RepoRoot -CreateIfMissing
$root = [System.IO.Path]::GetFullPath($root)
Load-RepoUrlsFromEnv -RepoRoot $root
$repoCreated = Initialize-RepositoryIfMissing -Root $root
Set-Location $root
Ensure-OriginRemote

if ($repoCreated) {
    Write-Host "Repository initialized on branch main" -ForegroundColor Cyan
}

$currentBuffer = git config --global http.postBuffer 2>$null
if (-not $currentBuffer) {
    git config --global http.postBuffer 524288000 | Out-Null
    Write-Host "Git http.postBuffer set to 524288000" -ForegroundColor Cyan
}

$branch = (git branch --show-current).Trim()
if (-not $branch) {
    throw "Detached HEAD detected. Cannot auto-commit and push."
}

git add -A

$status = git status --porcelain
if ($status) {
    if (-not $Message) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $Message = "Auto commit $timestamp"
    }

    git commit -m $Message
    Write-Host "Committed on branch $branch" -ForegroundColor Green
} else {
    Write-Host "No changes to commit" -ForegroundColor Yellow
}

if ($NoPush) {
    Write-Host "Skip push because -NoPush was specified" -ForegroundColor Yellow
} else {
    git push -u origin $branch
    Write-Host "Pushed to origin/$branch" -ForegroundColor Green
}
