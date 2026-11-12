# Windows PowerShell 5.1-compatible launcher; this script does not contact routers.
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $project
if (-not (Test-Path -LiteralPath (Join-Path $project 'AGENTS.md'))) { throw 'AGENTS.md is missing. Run from the project overlay root.' }
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw 'Node.js not found. Install official Node.js 24.9+ and re-open PowerShell.' }
$version = (& node --version).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read node --version.' }
$semver = $version.TrimStart('v').Split('.')
$major = [int]$semver[0]; $minor = [int]$semver[1]
if ($major -lt 24 -or ($major -eq 24 -and $minor -lt 9)) { Write-Warning "Node $version detected. Node 24.9+ is recommended for current DSH." }
$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { throw 'npx.cmd not found. Install Node.js/npm and re-open PowerShell.' }
Write-Host "Workspace: $project"
Write-Host 'DSH UI: http://127.0.0.1:3080 (default). Choose this workspace in UI.'
Write-Host 'Configure API credentials in Settings -> Models, not in repository files.'
Write-Host 'Press Ctrl+C in this console to stop the server.'
& npx.cmd '@deepseek-ai/dsh' web
if ($LASTEXITCODE -ne 0) { throw "DeepSeek Harness exited with code $LASTEXITCODE" }
