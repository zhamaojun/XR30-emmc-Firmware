# Optional GitHub Actions dispatch; requires gh auth and code already pushed to own Fork.
param(
    [ValidateSet('baseline','performance','full')][string]$Profile='baseline',
    [string]$Ref='ab766cbcb0cc22a64e8bf816443bf3e1a56614bd',
    [string]$Branch=''
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repo
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'gh CLI missing. Install GitHub CLI and run gh auth login.' }
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'gh auth failed.' }
$origin = (& git remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -notmatch 'github\.com[:/][^/]+/[^/]+(\.git)?$') { throw 'Expected a GitHub origin remote.' }
if ($origin -match 'github\.com[:/]Star-Song/Actions-rax3000z-emmc(\.git)?$') { throw "Refusing to dispatch CI against author's repo." }
if (-not $Branch) { $Branch = (& git branch --show-current).Trim() }
if (-not $Branch -or $Branch -eq 'main' -or $Branch -eq 'master') { throw 'Refuse dispatch from default branch; use feature branch.' }
& gh workflow run build-xr30-custom.yml --ref $Branch -f "profile=$Profile" -f "source_ref=$Ref"
if ($LASTEXITCODE -ne 0) { throw 'GitHub Actions dispatch failed (ensure branch/workflow has been pushed).' }
Write-Host "CI requested on $Branch, profile=$Profile. Inspect gh run list / GitHub Actions for actual result."
